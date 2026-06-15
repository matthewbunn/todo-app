#!/usr/bin/env python3
"""Self-hosted to-do app v4 — Python stdlib only.

Adds on top of v3 (projects, kanban, labels, subtasks, comments, activity):
recurring tasks, reminders + notifications (ntfy/Telegram/email), natural-language
quick-add, webhooks, task dependencies, attachments, time tracking, archive,
calendar + iCal feed, analytics, saved views, opt-in auth + API tokens, and PWA.
"""
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import smtplib
import sqlite3
import ssl
import threading
import time
import urllib.request
from datetime import datetime, date, timedelta, timezone
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import urlparse, parse_qs

DB_PATH = os.environ.get("DB_PATH", "/data/todo.db")
PORT = int(os.environ.get("PORT", "8080"))
ATTACH_DIR = os.environ.get("ATTACH_DIR", os.path.join(os.path.dirname(DB_PATH) or ".", "attachments"))
MAX_UPLOAD = 25 * 1024 * 1024


def _load_icons():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons.json")
        with open(path) as f:
            return {k: base64.b64decode(v) for k, v in json.load(f).items()}
    except Exception:
        return {}


ICON_PNGS = _load_icons()

PRIORITIES = ("none", "low", "medium", "high")
RECURRENCE = ("", "daily", "weekdays", "weekly", "biweekly", "monthly", "yearly")
WEBHOOK_EVENTS = ("task.created", "task.updated", "task.completed", "task.deleted")

_lock = threading.Lock()


def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------
# schema + migrations
# --------------------------------------------------------------------------
def init_db():
    if os.path.dirname(DB_PATH):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(ATTACH_DIR, exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#4a7dff',
                key TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0,
                is_done INTEGER NOT NULL DEFAULT 0,
                wip_limit INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'todo',
                priority TEXT NOT NULL DEFAULT 'none',
                due_date TEXT,
                project_id INTEGER,
                column_id INTEGER,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                archived INTEGER NOT NULL DEFAULT 0,
                recurrence TEXT NOT NULL DEFAULT '',
                reminder_at TEXT,
                reminded INTEGER NOT NULL DEFAULT 0,
                estimate_min INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS subtasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                position INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#7a8089'
            );
            CREATE TABLE IF NOT EXISTS task_labels (
                task_id INTEGER NOT NULL,
                label_id INTEGER NOT NULL,
                PRIMARY KEY (task_id, label_id)
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS task_deps (
                task_id INTEGER NOT NULL,
                depends_on_id INTEGER NOT NULL,
                PRIMARY KEY (task_id, depends_on_id)
            );
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                size INTEGER NOT NULL DEFAULT 0,
                mime TEXT NOT NULL DEFAULT 'application/octet-stream',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS time_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                minutes INTEGER NOT NULL DEFAULT 0,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS saved_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                config TEXT NOT NULL DEFAULT '{}',
                position INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS webhooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                events TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_used TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );
            """
        )
        # ---- migrate older tasks tables in place ----
        tcols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks)")}
        added_status = False
        added_column_id = False
        for col, ddl in (
            ("notes", "ALTER TABLE tasks ADD COLUMN notes TEXT NOT NULL DEFAULT ''"),
            ("status", "ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'todo'"),
            ("priority", "ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'none'"),
            ("due_date", "ALTER TABLE tasks ADD COLUMN due_date TEXT"),
            ("project_id", "ALTER TABLE tasks ADD COLUMN project_id INTEGER"),
            ("column_id", "ALTER TABLE tasks ADD COLUMN column_id INTEGER"),
            ("position", "ALTER TABLE tasks ADD COLUMN position INTEGER NOT NULL DEFAULT 0"),
            ("completed_at", "ALTER TABLE tasks ADD COLUMN completed_at TEXT"),
            ("archived", "ALTER TABLE tasks ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"),
            ("recurrence", "ALTER TABLE tasks ADD COLUMN recurrence TEXT NOT NULL DEFAULT ''"),
            ("reminder_at", "ALTER TABLE tasks ADD COLUMN reminder_at TEXT"),
            ("reminded", "ALTER TABLE tasks ADD COLUMN reminded INTEGER NOT NULL DEFAULT 0"),
            ("estimate_min", "ALTER TABLE tasks ADD COLUMN estimate_min INTEGER NOT NULL DEFAULT 0"),
        ):
            if col not in tcols:
                conn.execute(ddl)
                if col == "status":
                    added_status = True
                if col == "column_id":
                    added_column_id = True
                if col == "position":
                    conn.execute("UPDATE tasks SET position = id")
        if added_status:
            conn.execute("UPDATE tasks SET status = CASE WHEN done = 1 THEN 'done' ELSE 'todo' END")
        pcols = {r["name"] for r in conn.execute("PRAGMA table_info(projects)")}
        if "key" not in pcols:
            conn.execute("ALTER TABLE projects ADD COLUMN key TEXT")
        # ---- defaults ----
        if conn.execute("SELECT COUNT(*) c FROM columns").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO columns (name, position, is_done) VALUES (?, ?, ?)",
                [("To Do", 0, 0), ("In Progress", 1, 0), ("Done", 2, 1)],
            )
        if added_column_id or conn.execute(
            "SELECT COUNT(*) c FROM tasks WHERE column_id IS NULL"
        ).fetchone()["c"]:
            ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM columns")}
            first = conn.execute("SELECT id FROM columns ORDER BY position LIMIT 1").fetchone()["id"]
            done_col = conn.execute(
                "SELECT id FROM columns WHERE is_done = 1 ORDER BY position DESC LIMIT 1"
            )
            done_id = (done_col.fetchone() or {"id": first})["id"]
            conn.execute(
                "UPDATE tasks SET column_id = CASE status"
                " WHEN 'doing' THEN ? WHEN 'done' THEN ? ELSE ? END"
                " WHERE column_id IS NULL OR column_id NOT IN (SELECT id FROM columns)",
                (ids.get("In Progress", first), done_id, ids.get("To Do", first)),
            )
        # backfill completed_at for already-done tasks
        conn.execute(
            "UPDATE tasks SET completed_at = COALESCE(completed_at, created_at) "
            "WHERE done = 1 AND completed_at IS NULL"
        )
        ensure_default_project(conn)
        for p in conn.execute("SELECT id, name, key FROM projects").fetchall():
            if not p["key"]:
                conn.execute("UPDATE projects SET key = ? WHERE id = ?", (derive_key(conn, p["name"]), p["id"]))
        # one-time generated secrets
        if not get_setting(conn, "session_secret"):
            set_setting(conn, "session_secret", secrets.token_urlsafe(32))
        if not get_setting(conn, "feed_token"):
            set_setting(conn, "feed_token", secrets.token_urlsafe(16))


def ensure_default_project(conn):
    if conn.execute("SELECT COUNT(*) c FROM projects").fetchone()["c"] == 0:
        conn.execute(
            "INSERT INTO projects (name, color, key) VALUES ('Inbox', '#4a7dff', 'INBX')"
        )
    conn.execute(
        "UPDATE tasks SET project_id = (SELECT MIN(id) FROM projects) WHERE project_id IS NULL "
        "OR project_id NOT IN (SELECT id FROM projects)"
    )


def derive_key(conn, name):
    words = re.findall(r"[A-Za-z0-9]+", name or "")
    if not words:
        base = "PRJ"
    elif len(words) == 1:
        base = words[0][:4].upper()
    else:
        base = "".join(w[0] for w in words[:4]).upper()
    base = base or "PRJ"
    key, n = base, 2
    while conn.execute("SELECT 1 FROM projects WHERE key = ?", (key,)).fetchone():
        key = f"{base}{n}"
        n += 1
    return key


# --------------------------------------------------------------------------
# settings
# --------------------------------------------------------------------------
def get_setting(conn, key, default=""):
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn, key, value):
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value if value is not None else ""),
    )


# notification + auth setting keys exposed (non-secret) to the UI
NOTIFY_KEYS = (
    "ntfy_url", "ntfy_topic", "telegram_bot_token", "telegram_chat_id",
    "smtp_host", "smtp_port", "smtp_user", "smtp_pass", "smtp_from", "smtp_to",
)


# --------------------------------------------------------------------------
# auth helpers
# --------------------------------------------------------------------------
def hash_password(pw):
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000)
    return salt.hex() + "$" + dk.hex()


def verify_password(pw, stored):
    try:
        salt_hex, dk_hex = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt_hex), 200_000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, AttributeError):
        return False


def sign_session(conn, expiry_ts):
    secret = get_setting(conn, "session_secret").encode()
    payload = base64.urlsafe_b64encode(str(expiry_ts).encode()).decode()
    sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return payload + "." + sig


def check_session(conn, cookie_val):
    if not cookie_val or "." not in cookie_val:
        return False
    payload, sig = cookie_val.rsplit(".", 1)
    secret = get_setting(conn, "session_secret").encode()
    expect = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, sig):
        return False
    try:
        expiry = int(base64.urlsafe_b64decode(payload.encode()).decode())
    except (ValueError, Exception):
        return False
    return expiry > int(time.time())


# --------------------------------------------------------------------------
# notifications
# --------------------------------------------------------------------------
def _post(url, data=None, headers=None, method="POST"):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        return resp.status


def send_ntfy(cfg, title, body):
    url = (cfg.get("ntfy_url") or "https://ntfy.sh").rstrip("/")
    topic = cfg.get("ntfy_topic")
    if not topic:
        return None
    return _post(
        f"{url}/{topic}",
        data=body.encode("utf-8"),
        headers={"Title": title, "Content-Type": "text/plain; charset=utf-8"},
    )


def send_telegram(cfg, title, body):
    tok = cfg.get("telegram_bot_token")
    chat = cfg.get("telegram_chat_id")
    if not tok or not chat:
        return None
    payload = json.dumps({"chat_id": chat, "text": f"*{title}*\n{body}", "parse_mode": "Markdown"}).encode()
    return _post(
        f"https://api.telegram.org/bot{tok}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )


def send_email(cfg, title, body):
    host = cfg.get("smtp_host")
    if not host:
        return None
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = cfg.get("smtp_from") or cfg.get("smtp_user") or "todo@localhost"
    msg["To"] = cfg.get("smtp_to") or cfg.get("smtp_user")
    msg.set_content(body)
    port = int(cfg.get("smtp_port") or 587)
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15) as s:
            if cfg.get("smtp_user"):
                s.login(cfg["smtp_user"], cfg.get("smtp_pass") or "")
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.ehlo()
            try:
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
            except smtplib.SMTPException:
                pass
            if cfg.get("smtp_user"):
                s.login(cfg["smtp_user"], cfg.get("smtp_pass") or "")
            s.send_message(msg)
    return 200


def notify(title, body, only=None):
    """Send a notification through every configured channel. Returns per-channel result."""
    with db() as conn:
        cfg = {k: get_setting(conn, k) for k in NOTIFY_KEYS}
    results = {}
    channels = {"ntfy": send_ntfy, "telegram": send_telegram, "email": send_email}
    for name, fn in channels.items():
        if only and name not in only:
            continue
        try:
            r = fn(cfg, title, body)
            results[name] = "sent" if r else "not-configured"
        except Exception as e:  # noqa: BLE001 - report, never crash the request
            results[name] = f"error: {e.__class__.__name__}: {e}"
    return results


def notify_async(title, body):
    threading.Thread(target=notify, args=(title, body), daemon=True).start()


# --------------------------------------------------------------------------
# webhooks
# --------------------------------------------------------------------------
def fire_event(event, payload):
    def run():
        try:
            with db() as conn:
                hooks = conn.execute(
                    "SELECT * FROM webhooks WHERE active = 1"
                ).fetchall()
        except Exception:
            return
        body = json.dumps({"event": event, "data": payload, "at": now_utc()}).encode()
        for h in hooks:
            wants = [e for e in (h["events"] or "").split(",") if e]
            if wants and event not in wants:
                continue
            try:
                _post(h["url"], data=body, headers={"Content-Type": "application/json"})
            except Exception:
                pass
    threading.Thread(target=run, daemon=True).start()


# --------------------------------------------------------------------------
# recurrence + natural language
# --------------------------------------------------------------------------
def next_due(d, rule):
    """Given an ISO date string (or None) and a recurrence rule, return the next date."""
    try:
        base = datetime.strptime(d, "%Y-%m-%d").date() if d else date.today()
    except ValueError:
        base = date.today()
    if base < date.today():
        base = date.today()
    if rule == "daily":
        return (base + timedelta(days=1)).isoformat()
    if rule == "weekdays":
        nxt = base + timedelta(days=1)
        while nxt.weekday() >= 5:
            nxt += timedelta(days=1)
        return nxt.isoformat()
    if rule == "weekly":
        return (base + timedelta(weeks=1)).isoformat()
    if rule == "biweekly":
        return (base + timedelta(weeks=2)).isoformat()
    if rule == "monthly":
        m = base.month + 1
        y = base.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        day = min(base.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28,
                             31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
        return date(y, m, day).isoformat()
    if rule == "yearly":
        try:
            return base.replace(year=base.year + 1).isoformat()
        except ValueError:
            return date(base.year + 1, 3, 1).isoformat()
    return None


WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
            "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def parse_date_phrase(text):
    """Return (iso_date or None, leftover_text). Removes the matched phrase from text."""
    t = text
    low = t.lower()

    def cut(span):
        return (t[:span[0]] + t[span[1]:]).strip()

    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", low)
    if m:
        return m.group(1), cut(m.span())
    m = re.search(r"\bin (\d{1,3}) (day|days|week|weeks)\b", low)
    if m:
        n = int(m.group(1)) * (7 if m.group(2).startswith("week") else 1)
        return (date.today() + timedelta(days=n)).isoformat(), cut(m.span())
    m = re.search(r"\btoday\b", low)
    if m:
        return date.today().isoformat(), cut(m.span())
    m = re.search(r"\btomorrow\b", low)
    if m:
        return (date.today() + timedelta(days=1)).isoformat(), cut(m.span())
    m = re.search(r"\bnext (week|month)\b", low)
    if m:
        d = date.today() + timedelta(days=7 if m.group(1) == "week" else 30)
        return d.isoformat(), cut(m.span())
    m = re.search(r"\b(next )?(" + "|".join(WEEKDAYS) + r")\b", low)
    if m:
        target = WEEKDAYS[m.group(2)]
        delta = (target - date.today().weekday()) % 7
        delta = delta or 7
        if m.group(1):
            delta = delta if delta > 0 else 7
        return (date.today() + timedelta(days=delta)).isoformat(), cut(m.span())
    m = re.search(r"\b(" + "|".join(MONTHS) + r")[a-z]* (\d{1,2})\b", low)
    if m:
        mo = MONTHS[m.group(1)]
        day = int(m.group(2))
        y = date.today().year
        try:
            d = date(y, mo, day)
            if d < date.today():
                d = date(y + 1, mo, day)
            return d.isoformat(), cut(m.span())
        except ValueError:
            pass
    return None, t


def parse_quickadd(conn, text):
    """Parse '#project !high every week buy milk tomorrow' into a task payload dict."""
    out = {"title": "", "priority": "none", "due_date": None, "project_id": None,
           "label_ids": [], "recurrence": ""}
    t = " " + text.strip() + " "

    # recurrence: "every day/week/weekday/month/year" or "every monday"
    m = re.search(r"\bevery (day|weekday|weekdays|week|2 weeks|biweekly|month|year)\b", t, re.I)
    if m:
        word = m.group(1).lower()
        out["recurrence"] = {"day": "daily", "weekday": "weekdays", "weekdays": "weekdays",
                             "week": "weekly", "2 weeks": "biweekly", "biweekly": "biweekly",
                             "month": "monthly", "year": "yearly"}[word]
        t = (t[:m.start()] + " " + t[m.end():])
    md = re.search(r"\bevery (" + "|".join(WEEKDAYS) + r")\b", t, re.I)
    if md and not out["recurrence"]:
        out["recurrence"] = "weekly"
        if not out["due_date"]:
            target = WEEKDAYS[md.group(1).lower()]
            delta = (target - date.today().weekday()) % 7 or 7
            out["due_date"] = (date.today() + timedelta(days=delta)).isoformat()
        t = (t[:md.start()] + " " + t[md.end():])

    # priority: !high/!medium/!low or !p1/!p2/!p3
    m = re.search(r"(?:^|\s)!(high|medium|med|low|p1|p2|p3)\b", t, re.I)
    if m:
        v = m.group(1).lower()
        out["priority"] = {"high": "high", "p1": "high", "med": "medium", "medium": "medium",
                          "p2": "medium", "low": "low", "p3": "low"}[v]
        t = (t[:m.start()] + " " + t[m.end():])

    # project: #name (match by key or name, case-insensitive)
    for m in list(re.finditer(r"(?:^|\s)#([A-Za-z0-9_-]+)", t)):
        token = m.group(1)
        row = conn.execute(
            "SELECT id FROM projects WHERE lower(key)=lower(?) OR lower(name)=lower(?) "
            "OR lower(name) LIKE lower(?) ORDER BY id LIMIT 1",
            (token, token.replace("_", " "), token.replace("_", " ") + "%"),
        ).fetchone()
        if row:
            out["project_id"] = row["id"]
            t = (t[:m.start()] + " " + t[m.end():])
            break

    # labels: @name (create if missing)
    for m in list(re.finditer(r"(?:^|\s)@([A-Za-z0-9_-]+)", t)):
        name = m.group(1).replace("_", " ")
        row = conn.execute("SELECT id FROM labels WHERE lower(name)=lower(?)", (name,)).fetchone()
        if not row:
            cur = conn.execute("INSERT INTO labels (name, color) VALUES (?, ?)",
                               (name[:50], "#7a8089"))
            lid = cur.lastrowid
        else:
            lid = row["id"]
        if lid not in out["label_ids"]:
            out["label_ids"].append(lid)
    t = re.sub(r"(?:^|\s)@[A-Za-z0-9_-]+", " ", t)

    # date phrase
    d, t = parse_date_phrase(t.strip())
    if d:
        out["due_date"] = d

    out["title"] = re.sub(r"\s+", " ", t).strip()
    return out


# --------------------------------------------------------------------------
# task helpers
# --------------------------------------------------------------------------
def get_task(conn, task_id):
    return conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def task_dict(row):
    d = dict(row)
    d.pop("done", None)
    d.pop("status", None)
    return d


def log_activity(conn, task_id, text):
    conn.execute("INSERT INTO activity (task_id, text) VALUES (?, ?)", (task_id, text[:300]))


def spawn_recurrence(conn, task):
    """When a recurring task is completed, create the next occurrence and stop the original."""
    rule = task["recurrence"]
    if rule not in RECURRENCE or not rule:
        return
    nd = next_due(task["due_date"], rule)
    first_col = conn.execute("SELECT id FROM columns ORDER BY position LIMIT 1").fetchone()
    if not first_col:
        return
    pos = conn.execute(
        "SELECT COALESCE(MAX(position)+1,0) p FROM tasks WHERE project_id=? AND column_id=?",
        (task["project_id"], first_col["id"]),
    ).fetchone()["p"]
    new_reminder = None
    if task["reminder_at"] and task["due_date"] and nd:
        try:
            delta = (datetime.strptime(task["due_date"], "%Y-%m-%d").date()
                     - datetime.strptime(task["reminder_at"][:10], "%Y-%m-%d").date())
            new_reminder = (datetime.strptime(nd, "%Y-%m-%d") - delta).strftime("%Y-%m-%d ") + task["reminder_at"][11:]
        except (ValueError, IndexError):
            new_reminder = None
    cur = conn.execute(
        "INSERT INTO tasks (title, notes, priority, due_date, project_id, column_id, position, done,"
        " recurrence, reminder_at, estimate_min) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
        (task["title"], task["notes"], task["priority"], nd, task["project_id"],
         first_col["id"], pos, rule, new_reminder, task["estimate_min"]),
    )
    new_id = cur.lastrowid
    for lid in conn.execute("SELECT label_id FROM task_labels WHERE task_id=?", (task["id"],)):
        conn.execute("INSERT OR IGNORE INTO task_labels (task_id, label_id) VALUES (?, ?)",
                     (new_id, lid["label_id"]))
    log_activity(conn, new_id, "Created from recurring task " + str(task["id"]))
    # stop the completed instance from recurring again
    conn.execute("UPDATE tasks SET recurrence='' WHERE id=?", (task["id"],))


def move_task(conn, task, column_id=None, project_id=None, index=None):
    valid_col = column_id is not None and conn.execute(
        "SELECT 1 FROM columns WHERE id = ?", (column_id,)
    ).fetchone()
    new_col = column_id if valid_col else task["column_id"]
    new_proj = project_id if project_id is not None else task["project_id"]
    rows = [
        r["id"]
        for r in conn.execute(
            "SELECT id FROM tasks WHERE project_id = ? AND column_id = ? AND id != ? ORDER BY position",
            (new_proj, new_col, task["id"]),
        )
    ]
    if index is None or not isinstance(index, int) or index > len(rows):
        index = len(rows)
    index = max(0, index)
    rows.insert(index, task["id"])
    for i, tid in enumerate(rows):
        conn.execute("UPDATE tasks SET position = ? WHERE id = ?", (i, tid))
    is_done = (conn.execute("SELECT is_done FROM columns WHERE id = ?", (new_col,)).fetchone()
               or {"is_done": 0})["is_done"]
    was_done = task["done"]
    completed_at = task["completed_at"]
    if is_done and not was_done:
        completed_at = now_utc()
    elif not is_done:
        completed_at = None
    conn.execute(
        "UPDATE tasks SET column_id = ?, project_id = ?, done = ?, completed_at = ? WHERE id = ?",
        (new_col, new_proj, is_done, completed_at, task["id"]),
    )
    if valid_col and column_id != task["column_id"]:
        name = conn.execute("SELECT name FROM columns WHERE id = ?", (new_col,)).fetchone()["name"]
        log_activity(conn, task["id"], f"Moved to {name}")
    if is_done and not was_done:
        fresh = get_task(conn, task["id"])
        spawn_recurrence(conn, fresh)
        return "completed"
    return None


def delete_task_cascade(conn, task_id):
    for fn in (
        "DELETE FROM subtasks WHERE task_id = ?",
        "DELETE FROM comments WHERE task_id = ?",
        "DELETE FROM activity WHERE task_id = ?",
        "DELETE FROM task_labels WHERE task_id = ?",
        "DELETE FROM task_deps WHERE task_id = ? OR depends_on_id = ?",
        "DELETE FROM time_logs WHERE task_id = ?",
    ):
        conn.execute(fn, (task_id, task_id) if "depends_on_id" in fn else (task_id,))
    for a in conn.execute("SELECT stored_name FROM attachments WHERE task_id = ?", (task_id,)):
        try:
            os.remove(os.path.join(ATTACH_DIR, a["stored_name"]))
        except OSError:
            pass
    conn.execute("DELETE FROM attachments WHERE task_id = ?", (task_id,))
    return conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def blocked_map(conn):
    """task_id -> list of blocking (incomplete) dependency ids."""
    out = {}
    done_cols = {r["id"] for r in conn.execute("SELECT id FROM columns WHERE is_done=1")}
    deps = conn.execute("SELECT task_id, depends_on_id FROM task_deps").fetchall()
    states = {r["id"]: r["column_id"] for r in conn.execute("SELECT id, column_id FROM tasks")}
    for d in deps:
        if states.get(d["depends_on_id"]) not in done_cols and d["depends_on_id"] in states:
            out.setdefault(d["task_id"], []).append(d["depends_on_id"])
    return out


# --------------------------------------------------------------------------
# scheduler: due reminders
# --------------------------------------------------------------------------
def scheduler_loop():
    while True:
        try:
            run_reminders()
        except Exception:
            pass
        time.sleep(45)


def run_reminders():
    now = now_utc()
    due = []
    with _lock, db() as conn:
        rows = conn.execute(
            "SELECT t.*, p.name pname, p.key pkey FROM tasks t LEFT JOIN projects p ON p.id=t.project_id "
            "WHERE t.reminder_at IS NOT NULL AND t.reminded=0 AND t.done=0 AND t.archived=0 "
            "AND t.reminder_at <= ?",
            (now,),
        ).fetchall()
        for r in rows:
            due.append(dict(r))
            conn.execute("UPDATE tasks SET reminded=1 WHERE id=?", (r["id"],))
    for r in due:
        key = (r.get("pkey") or "TASK") + "-" + str(r["id"])
        body = r["title"]
        if r.get("due_date"):
            body += f"\nDue {r['due_date']}"
        if r.get("pname"):
            body += f"\nProject: {r['pname']}"
        notify(f"Reminder: {key}", body)
        fire_event("task.updated", {"id": r["id"], "reminder": True})


# --------------------------------------------------------------------------
# multipart parsing (stdlib only)
# --------------------------------------------------------------------------
def parse_multipart(body, content_type):
    """Minimal multipart/form-data parser. Returns (fields dict, files list)."""
    m = re.search(r"boundary=([^;]+)", content_type)
    if not m:
        return {}, []
    boundary = m.group(1).strip().strip('"').encode()
    delim = b"--" + boundary
    fields, files = {}, []
    for part in body.split(delim):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if b"\r\n\r\n" not in part:
            continue
        head, data = part.split(b"\r\n\r\n", 1)
        head_text = head.decode("utf-8", "replace")
        disp = re.search(r'name="([^"]*)"', head_text)
        if not disp:
            continue
        name = disp.group(1)
        fn = re.search(r'filename="([^"]*)"', head_text)
        if fn and fn.group(1):
            ct = re.search(r"Content-Type:\s*([^\r\n]+)", head_text, re.I)
            files.append({
                "field": name, "filename": fn.group(1),
                "content_type": ct.group(1).strip() if ct else "application/octet-stream",
                "data": data,
            })
        else:
            fields[name] = data.decode("utf-8", "replace")
    return fields, files


# --------------------------------------------------------------------------
# HTTP handler
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "TodoApp/4.0"

    # ---- low-level senders ----
    def _cors_headers(self):
        # Allow a locally-bundled desktop client (file/app origin) to call the LAN API.
        origin = self.headers.get("Origin")
        return {
            "Access-Control-Allow-Origin": origin or "*",
            "Vary": "Origin",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
        }

    def _send(self, code, body=b"", content_type="application/json", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in self._cors_headers().items():
            self.send_header(k, v)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204)

    def _json(self, code, obj, extra=None):
        self._send(code, json.dumps(obj).encode(), extra=extra)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return b""
        if length > MAX_UPLOAD + 1024:
            return None
        return self.rfile.read(length)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        if length > 10_000_000:
            return None
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _route(self):
        parsed = urlparse(self.path)
        return [p for p in parsed.path.split("/") if p], parse_qs(parsed.query)

    @staticmethod
    def _int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    # ---- auth ----
    def _authed(self, query=None):
        """True if the request may proceed. Open when no password is set."""
        with db() as conn:
            pw = get_setting(conn, "password_hash")
            if not pw:
                return True
            # bearer token
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                tok = auth[7:].strip()
                row = conn.execute("SELECT id FROM tokens WHERE token=?", (tok,)).fetchone()
                if row:
                    conn.execute("UPDATE tokens SET last_used=? WHERE id=?", (now_utc(), row["id"]))
                    return True
            # session cookie
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            if "sid" in cookie and check_session(conn, cookie["sid"].value):
                return True
            # feed token (read-only) for ?token=
            if query and query.get("token"):
                if query["token"][0] == get_setting(conn, "feed_token"):
                    return True
        return False

    # ---------------- GET ----------------
    def do_GET(self):
        parts, query = self._route()
        # ---- always-public routes ----
        if not parts or parts[0] == "index.html":
            return self._send(200, INDEX, "text/html; charset=utf-8")
        if parts == ["healthz"]:
            return self._send(200, b"ok", "text/plain")
        if parts == ["manifest.webmanifest"]:
            return self._send(200, MANIFEST, "application/manifest+json")
        if parts == ["sw.js"]:
            return self._send(200, SW_JS, "application/javascript")
        if parts == ["icon.svg"]:
            return self._send(200, ICON_SVG, "image/svg+xml")
        if len(parts) == 1 and parts[0] in ICON_PNGS:
            return self._send(200, ICON_PNGS[parts[0]], "image/png")
        if parts == ["api", "me"]:
            return self._me()
        if parts == ["ical"]:
            return self._ical(query)
        # ---- gated routes ----
        if not self._authed(query):
            return self._json(401, {"error": "auth required"})
        if parts == ["api", "state"]:
            return self._state(query)
        if parts == ["api", "stats"]:
            return self._stats()
        if parts == ["api", "export"]:
            return self._export()
        if parts == ["api", "settings"]:
            return self._get_settings()
        if parts == ["api", "tokens"]:
            return self._list_tokens()
        if parts == ["api", "webhooks"]:
            return self._list_webhooks()
        if len(parts) == 3 and parts[:2] == ["api", "tasks"]:
            return self._task_detail(self._int(parts[2]))
        if len(parts) == 3 and parts[:2] == ["api", "attachments"]:
            return self._download_attachment(self._int(parts[2]))
        self._json(404, {"error": "not found"})

    def _me(self):
        with db() as conn:
            has_pw = bool(get_setting(conn, "password_hash"))
        return self._json(200, {"auth_required": has_pw, "authed": self._authed(), "version": 4})

    def _state(self, query):
        project = (query.get("project") or ["all"])[0]
        include_archived = (query.get("archived") or ["0"])[0] == "1"
        with _lock, db() as conn:
            projects = [dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY id")]
            open_c, total_c = {}, {}
            for r in conn.execute(
                "SELECT t.project_id pid, c.is_done d, COUNT(*) n FROM tasks t"
                " JOIN columns c ON c.id = t.column_id WHERE t.archived=0 GROUP BY t.project_id, c.is_done"
            ):
                total_c[r["pid"]] = total_c.get(r["pid"], 0) + r["n"]
                if not r["d"]:
                    open_c[r["pid"]] = open_c.get(r["pid"], 0) + r["n"]
            for p in projects:
                p["open"] = open_c.get(p["id"], 0)
                p["total"] = total_c.get(p["id"], 0)
            columns = [dict(r) for r in conn.execute("SELECT * FROM columns ORDER BY position")]
            labels = [dict(r) for r in conn.execute("SELECT * FROM labels ORDER BY name")]
            saved = [dict(r) for r in conn.execute("SELECT * FROM saved_views ORDER BY position, id")]
            arch_clause = "" if include_archived else " AND archived=0"
            if project == "all":
                rows = conn.execute(f"SELECT * FROM tasks WHERE 1=1{arch_clause} ORDER BY position").fetchall()
            elif project == "archived":
                rows = conn.execute("SELECT * FROM tasks WHERE archived=1 ORDER BY id DESC").fetchall()
            else:
                pid = self._int(project)
                if pid is None:  # unknown scope (e.g. a UI-only view): fall back to all tasks
                    rows = conn.execute(
                        f"SELECT * FROM tasks WHERE 1=1{arch_clause} ORDER BY position").fetchall()
                else:
                    rows = conn.execute(
                        f"SELECT * FROM tasks WHERE project_id = ?{arch_clause} ORDER BY position", (pid,)
                    ).fetchall()
            tasks = [task_dict(r) for r in rows]
            subs, coms, tls, atts, logs = {}, {}, {}, {}, {}
            for r in conn.execute("SELECT task_id, COUNT(*) n, SUM(done) d FROM subtasks GROUP BY task_id"):
                subs[r["task_id"]] = (r["n"], r["d"] or 0)
            for r in conn.execute("SELECT task_id, COUNT(*) n FROM comments GROUP BY task_id"):
                coms[r["task_id"]] = r["n"]
            for r in conn.execute("SELECT task_id, label_id FROM task_labels"):
                tls.setdefault(r["task_id"], []).append(r["label_id"])
            for r in conn.execute("SELECT task_id, COUNT(*) n FROM attachments GROUP BY task_id"):
                atts[r["task_id"]] = r["n"]
            for r in conn.execute("SELECT task_id, COALESCE(SUM(minutes),0) m FROM time_logs GROUP BY task_id"):
                logs[r["task_id"]] = r["m"]
            blocked = blocked_map(conn)
            for t in tasks:
                n, d = subs.get(t["id"], (0, 0))
                t["subtasks_total"], t["subtasks_done"] = n, d
                t["comments"] = coms.get(t["id"], 0)
                t["label_ids"] = tls.get(t["id"], [])
                t["attachments"] = atts.get(t["id"], 0)
                t["logged_min"] = logs.get(t["id"], 0)
                t["blocked_by"] = blocked.get(t["id"], [])
        self._json(200, {"projects": projects, "columns": columns, "labels": labels,
                         "tasks": tasks, "saved_views": saved})

    def _stats(self):
        with _lock, db() as conn:
            cols = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM columns ORDER BY position")}
            by_col = []
            for cid, c in cols.items():
                n = conn.execute("SELECT COUNT(*) n FROM tasks WHERE column_id=? AND archived=0",
                                 (cid,)).fetchone()["n"]
                by_col.append({"name": c["name"], "count": n, "is_done": c["is_done"]})
            by_prio = {p: conn.execute(
                "SELECT COUNT(*) n FROM tasks WHERE priority=? AND archived=0 AND done=0", (p,)
            ).fetchone()["n"] for p in PRIORITIES}
            totals = {
                "open": conn.execute("SELECT COUNT(*) n FROM tasks WHERE done=0 AND archived=0").fetchone()["n"],
                "done": conn.execute("SELECT COUNT(*) n FROM tasks WHERE done=1 AND archived=0").fetchone()["n"],
                "archived": conn.execute("SELECT COUNT(*) n FROM tasks WHERE archived=1").fetchone()["n"],
                "overdue": conn.execute(
                    "SELECT COUNT(*) n FROM tasks t JOIN columns c ON c.id=t.column_id "
                    "WHERE t.due_date < ? AND c.is_done=0 AND t.archived=0", (date.today().isoformat(),)
                ).fetchone()["n"],
            }
            weeks = []
            for i in range(7, -1, -1):
                start = date.today() - timedelta(days=date.today().weekday() + 7 * i)
                end = start + timedelta(days=7)
                created = conn.execute(
                    "SELECT COUNT(*) n FROM tasks WHERE date(created_at) >= ? AND date(created_at) < ?",
                    (start.isoformat(), end.isoformat())).fetchone()["n"]
                completed = conn.execute(
                    "SELECT COUNT(*) n FROM tasks WHERE completed_at IS NOT NULL "
                    "AND date(completed_at) >= ? AND date(completed_at) < ?",
                    (start.isoformat(), end.isoformat())).fetchone()["n"]
                weeks.append({"week": start.isoformat(), "created": created, "completed": completed})
            logged = conn.execute("SELECT COALESCE(SUM(minutes),0) m FROM time_logs").fetchone()["m"]
        self._json(200, {"by_column": by_col, "by_priority": by_prio, "totals": totals,
                         "weeks": weeks, "logged_min": logged})

    def _task_detail(self, tid):
        with _lock, db() as conn:
            task = get_task(conn, tid)
            if task is None:
                return self._json(404, {"error": "task not found"})
            d = task_dict(task)
            d["subtasks"] = [dict(r) for r in conn.execute(
                "SELECT * FROM subtasks WHERE task_id = ? ORDER BY position, id", (tid,))]
            d["comments_list"] = [dict(r) for r in conn.execute(
                "SELECT * FROM comments WHERE task_id = ? ORDER BY id", (tid,))]
            d["activity"] = [dict(r) for r in conn.execute(
                "SELECT * FROM activity WHERE task_id = ? ORDER BY id DESC LIMIT 40", (tid,))]
            d["label_ids"] = [r["label_id"] for r in conn.execute(
                "SELECT label_id FROM task_labels WHERE task_id = ?", (tid,))]
            d["attachments"] = [dict(r) for r in conn.execute(
                "SELECT id, filename, size, mime, created_at FROM attachments WHERE task_id=? ORDER BY id", (tid,))]
            d["time_logs"] = [dict(r) for r in conn.execute(
                "SELECT * FROM time_logs WHERE task_id=? ORDER BY id DESC", (tid,))]
            d["logged_min"] = sum(r["minutes"] for r in d["time_logs"])
            d["depends_on"] = [r["depends_on_id"] for r in conn.execute(
                "SELECT depends_on_id FROM task_deps WHERE task_id=?", (tid,))]
            d["blocks"] = [r["task_id"] for r in conn.execute(
                "SELECT task_id FROM task_deps WHERE depends_on_id=?", (tid,))]
            d["blocked_by"] = blocked_map(conn).get(tid, [])
        self._json(200, d)

    def _download_attachment(self, aid):
        with _lock, db() as conn:
            row = conn.execute("SELECT * FROM attachments WHERE id=?", (aid,)).fetchone()
        if not row:
            return self._json(404, {"error": "attachment not found"})
        path = os.path.join(ATTACH_DIR, row["stored_name"])
        if not os.path.exists(path):
            return self._json(404, {"error": "file missing"})
        with open(path, "rb") as f:
            data = f.read()
        safe = row["filename"].replace('"', "")
        self._send(200, data, row["mime"],
                   extra={"Content-Disposition": f'attachment; filename="{safe}"'})

    def _export(self):
        tables = ("projects", "columns", "labels", "tasks", "subtasks", "task_labels",
                  "comments", "task_deps", "time_logs", "saved_views")
        with _lock, db() as conn:
            out = {"version": 4}
            for table in tables:
                out[table] = [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
        body = json.dumps(out, indent=1).encode()
        self._send(200, body, "application/json",
                   extra={"Content-Disposition": "attachment; filename=todo-backup.json"})

    def _ical(self, query):
        if not self._authed(query):
            return self._send(401, b"auth required", "text/plain")
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//todo-app//EN", "CALSCALE:GREGORIAN",
                 "X-WR-CALNAME:To-Do"]
        with _lock, db() as conn:
            rows = conn.execute(
                "SELECT t.*, p.key pkey FROM tasks t LEFT JOIN projects p ON p.id=t.project_id "
                "WHERE t.due_date IS NOT NULL AND t.archived=0").fetchall()
            done_cols = {r["id"] for r in conn.execute("SELECT id FROM columns WHERE is_done=1")}
        for r in rows:
            d = (r["due_date"] or "").replace("-", "")
            if len(d) != 8:
                continue
            try:
                dt_end = (datetime.strptime(r["due_date"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
            except ValueError:
                continue
            key = (r["pkey"] or "TASK") + "-" + str(r["id"])
            status = "COMPLETED" if r["column_id"] in done_cols else "NEEDS-ACTION"
            summary = ("[done] " if r["column_id"] in done_cols else "") + r["title"]
            lines += [
                "BEGIN:VEVENT", f"UID:task-{r['id']}@todo-app", f"DTSTART;VALUE=DATE:{d}",
                f"DTEND;VALUE=DATE:{dt_end}",
                "SUMMARY:" + summary.replace("\n", " ").replace(",", "\\,")[:200],
                f"DESCRIPTION:{key}", f"STATUS:{status}", "END:VEVENT",
            ]
        lines.append("END:VCALENDAR")
        body = ("\r\n".join(lines) + "\r\n").encode()
        self._send(200, body, "text/calendar; charset=utf-8")

    def _get_settings(self):
        with db() as conn:
            cfg = {k: get_setting(conn, k) for k in NOTIFY_KEYS}
            cfg["smtp_pass"] = "***" if cfg.get("smtp_pass") else ""
            cfg["telegram_bot_token"] = "***" if cfg.get("telegram_bot_token") else ""
            cfg["has_password"] = bool(get_setting(conn, "password_hash"))
            cfg["feed_token"] = get_setting(conn, "feed_token")
        self._json(200, cfg)

    def _list_tokens(self):
        with db() as conn:
            rows = conn.execute("SELECT id, name, created_at, last_used, token FROM tokens ORDER BY id").fetchall()
        out = [{"id": r["id"], "name": r["name"], "created_at": r["created_at"],
                "last_used": r["last_used"], "preview": r["token"][:6] + "…"} for r in rows]
        self._json(200, out)

    def _list_webhooks(self):
        with db() as conn:
            rows = [dict(r) for r in conn.execute("SELECT * FROM webhooks ORDER BY id")]
        self._json(200, rows)

    # ---------------- POST ----------------
    def do_POST(self):
        parts, query = self._route()
        # multipart attachment upload handled separately (binary body)
        if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "attachments":
            if not self._authed():
                return self._json(401, {"error": "auth required"})
            return self._upload_attachment(self._int(parts[2]))

        # login is public
        if parts == ["api", "login"]:
            return self._login()
        if parts == ["api", "logout"]:
            return self._send(204, extra={"Set-Cookie": "sid=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"})

        if not self._authed():
            return self._json(401, {"error": "auth required"})

        data = self._read_json()
        if data is None:
            return self._json(400, {"error": "invalid JSON"})

        if parts == ["api", "quickadd"]:
            return self._quickadd(data)
        if parts == ["api", "projects"]:
            return self._create_project(data)
        if parts == ["api", "columns"]:
            return self._create_column(data)
        if parts == ["api", "labels"]:
            return self._create_label(data)
        if parts == ["api", "tasks"]:
            return self._create_task(data)
        if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "subtasks":
            return self._create_subtask(self._int(parts[2]), data)
        if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "comments":
            return self._create_comment(self._int(parts[2]), data)
        if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "timelogs":
            return self._create_timelog(self._int(parts[2]), data)
        if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "deps":
            return self._add_dep(self._int(parts[2]), data)
        if parts == ["api", "saved_views"]:
            return self._create_saved_view(data)
        if parts == ["api", "webhooks"]:
            return self._create_webhook(data)
        if parts == ["api", "tokens"]:
            return self._create_token(data)
        if parts == ["api", "settings"]:
            return self._update_settings(data)
        if parts == ["api", "notify-test"]:
            return self._json(200, notify("Test from To-Do",
                                          "Notifications are working." , only=data.get("only")))
        if parts == ["api", "import"]:
            return self._import(data)
        self._json(404, {"error": "not found"})

    def _login(self):
        data = self._read_json() or {}
        with db() as conn:
            stored = get_setting(conn, "password_hash")
            if not stored:
                return self._json(200, {"ok": True, "auth_required": False})
            if not verify_password(str(data.get("password") or ""), stored):
                return self._json(401, {"error": "wrong password"})
            expiry = int(time.time()) + 30 * 86400
            sid = sign_session(conn, expiry)
        cookie = f"sid={sid}; Path=/; Max-Age={30*86400}; HttpOnly; SameSite=Lax"
        self._json(200, {"ok": True}, extra={"Set-Cookie": cookie})

    def _quickadd(self, data):
        text = (data.get("text") or "").strip()
        if not text:
            return self._json(400, {"error": "text is required"})
        with _lock, db() as conn:
            payload = parse_quickadd(conn, text)
            if not payload["title"]:
                payload["title"] = text
            tid = self._insert_task(conn, payload)
            row = get_task(conn, tid)
            result = task_dict(row)
            result["parsed"] = {k: payload[k] for k in ("priority", "due_date", "project_id",
                                                         "recurrence", "label_ids")}
        fire_event("task.created", {"id": tid, "title": row["title"]})
        return self._json(201, result)

    def _create_project(self, data):
        name = (data.get("name") or "").strip()
        if not name:
            return self._json(400, {"error": "name is required"})
        with _lock, db() as conn:
            key = (data.get("key") or "").strip().upper()[:6] or derive_key(conn, name)
            cur = conn.execute("INSERT INTO projects (name, color, key) VALUES (?, ?, ?)",
                               (name[:100], str(data.get("color") or "#4a7dff")[:20], key))
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._json(201, dict(row))

    def _create_column(self, data):
        name = (data.get("name") or "").strip()
        if not name:
            return self._json(400, {"error": "name is required"})
        with _lock, db() as conn:
            pos = conn.execute("SELECT COALESCE(MAX(position)+1,0) p FROM columns").fetchone()["p"]
            wip = self._int(data.get("wip_limit")) or 0
            cur = conn.execute(
                "INSERT INTO columns (name, position, is_done, wip_limit) VALUES (?, ?, ?, ?)",
                (name[:60], pos, 1 if data.get("is_done") else 0, max(0, wip)))
            row = conn.execute("SELECT * FROM columns WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._json(201, dict(row))

    def _create_label(self, data):
        name = (data.get("name") or "").strip()
        if not name:
            return self._json(400, {"error": "name is required"})
        with _lock, db() as conn:
            existing = conn.execute("SELECT * FROM labels WHERE lower(name) = lower(?)", (name,)).fetchone()
            if existing:
                return self._json(200, dict(existing))
            cur = conn.execute("INSERT INTO labels (name, color) VALUES (?, ?)",
                               (name[:50], str(data.get("color") or "#7a8089")[:20]))
            row = conn.execute("SELECT * FROM labels WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._json(201, dict(row))

    def _insert_task(self, conn, data):
        title = (data.get("title") or "").strip()
        priority = data.get("priority") if data.get("priority") in PRIORITIES else "none"
        recurrence = data.get("recurrence") if data.get("recurrence") in RECURRENCE else ""
        pid = self._int(data.get("project_id"))
        if pid is None or not conn.execute("SELECT 1 FROM projects WHERE id=?", (pid,)).fetchone():
            pid = conn.execute("SELECT MIN(id) m FROM projects").fetchone()["m"]
        cid = self._int(data.get("column_id"))
        if cid is None or not conn.execute("SELECT 1 FROM columns WHERE id=?", (cid,)).fetchone():
            cid = conn.execute("SELECT id FROM columns ORDER BY position LIMIT 1").fetchone()["id"]
        pos = conn.execute(
            "SELECT COALESCE(MAX(position)+1,0) p FROM tasks WHERE project_id=? AND column_id=?",
            (pid, cid)).fetchone()["p"]
        is_done = conn.execute("SELECT is_done FROM columns WHERE id=?", (cid,)).fetchone()["is_done"]
        cur = conn.execute(
            "INSERT INTO tasks (title, notes, priority, due_date, project_id, column_id, position, done,"
            " recurrence, reminder_at, estimate_min, completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (title[:500], str(data.get("notes") or "")[:10000], priority, data.get("due_date") or None,
             pid, cid, pos, is_done, recurrence, data.get("reminder_at") or None,
             max(0, self._int(data.get("estimate_min")) or 0), now_utc() if is_done else None))
        tid = cur.lastrowid
        for lid in data.get("label_ids") or []:
            if conn.execute("SELECT 1 FROM labels WHERE id=?", (self._int(lid),)).fetchone():
                conn.execute("INSERT OR IGNORE INTO task_labels (task_id, label_id) VALUES (?, ?)",
                             (tid, self._int(lid)))
        log_activity(conn, tid, "Created this task")
        return tid

    def _create_task(self, data):
        if not (data.get("title") or "").strip():
            return self._json(400, {"error": "title is required"})
        with _lock, db() as conn:
            tid = self._insert_task(conn, data)
            row = get_task(conn, tid)
        fire_event("task.created", {"id": tid, "title": row["title"]})
        return self._json(201, task_dict(row))

    def _create_subtask(self, tid, data):
        title = (data.get("title") or "").strip()
        if not title:
            return self._json(400, {"error": "title is required"})
        with _lock, db() as conn:
            if get_task(conn, tid) is None:
                return self._json(404, {"error": "task not found"})
            pos = conn.execute("SELECT COALESCE(MAX(position)+1,0) p FROM subtasks WHERE task_id=?",
                               (tid,)).fetchone()["p"]
            cur = conn.execute("INSERT INTO subtasks (task_id, title, position) VALUES (?, ?, ?)",
                               (tid, title[:300], pos))
            row = conn.execute("SELECT * FROM subtasks WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._json(201, dict(row))

    def _create_comment(self, tid, data):
        body = (data.get("body") or "").strip()
        if not body:
            return self._json(400, {"error": "body is required"})
        with _lock, db() as conn:
            if get_task(conn, tid) is None:
                return self._json(404, {"error": "task not found"})
            cur = conn.execute("INSERT INTO comments (task_id, body) VALUES (?, ?)", (tid, body[:5000]))
            log_activity(conn, tid, "Added a comment")
            row = conn.execute("SELECT * FROM comments WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._json(201, dict(row))

    def _create_timelog(self, tid, data):
        minutes = self._int(data.get("minutes"))
        if not minutes or minutes <= 0:
            return self._json(400, {"error": "minutes must be a positive integer"})
        with _lock, db() as conn:
            if get_task(conn, tid) is None:
                return self._json(404, {"error": "task not found"})
            cur = conn.execute("INSERT INTO time_logs (task_id, minutes, note) VALUES (?, ?, ?)",
                               (tid, min(minutes, 100000), str(data.get("note") or "")[:300]))
            log_activity(conn, tid, f"Logged {minutes} min")
            row = conn.execute("SELECT * FROM time_logs WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._json(201, dict(row))

    def _add_dep(self, tid, data):
        dep = self._int(data.get("depends_on_id"))
        if dep is None or dep == tid:
            return self._json(400, {"error": "invalid dependency"})
        with _lock, db() as conn:
            if get_task(conn, tid) is None or get_task(conn, dep) is None:
                return self._json(404, {"error": "task not found"})
            # prevent a direct cycle
            if conn.execute("SELECT 1 FROM task_deps WHERE task_id=? AND depends_on_id=?",
                            (dep, tid)).fetchone():
                return self._json(400, {"error": "that would create a circular dependency"})
            conn.execute("INSERT OR IGNORE INTO task_deps (task_id, depends_on_id) VALUES (?, ?)", (tid, dep))
            log_activity(conn, tid, f"Now depends on task {dep}")
        return self._json(201, {"ok": True})

    def _create_saved_view(self, data):
        name = (data.get("name") or "").strip()
        if not name:
            return self._json(400, {"error": "name is required"})
        with _lock, db() as conn:
            pos = conn.execute("SELECT COALESCE(MAX(position)+1,0) p FROM saved_views").fetchone()["p"]
            cur = conn.execute("INSERT INTO saved_views (name, config, position) VALUES (?, ?, ?)",
                               (name[:60], json.dumps(data.get("config") or {})[:4000], pos))
            row = conn.execute("SELECT * FROM saved_views WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._json(201, dict(row))

    def _create_webhook(self, data):
        url = (data.get("url") or "").strip()
        if not re.match(r"^https?://", url):
            return self._json(400, {"error": "valid http(s) url required"})
        events = ",".join(e for e in (data.get("events") or []) if e in WEBHOOK_EVENTS)
        with _lock, db() as conn:
            cur = conn.execute("INSERT INTO webhooks (url, events, active) VALUES (?, ?, 1)",
                               (url[:500], events))
            row = conn.execute("SELECT * FROM webhooks WHERE id=?", (cur.lastrowid,)).fetchone()
        return self._json(201, dict(row))

    def _create_token(self, data):
        name = (data.get("name") or "API token").strip()[:60]
        tok = secrets.token_urlsafe(24)
        with _lock, db() as conn:
            cur = conn.execute("INSERT INTO tokens (name, token) VALUES (?, ?)", (name, tok))
            tid = cur.lastrowid
        return self._json(201, {"id": tid, "name": name, "token": tok})

    def _update_settings(self, data):
        with _lock, db() as conn:
            # password set / clear
            if "password" in data:
                pw = str(data["password"])
                if pw == "":
                    conn.execute("DELETE FROM settings WHERE key='password_hash'")
                else:
                    set_setting(conn, "password_hash", hash_password(pw))
            for k in NOTIFY_KEYS:
                if k in data:
                    val = str(data[k])
                    if val == "***":  # unchanged masked secret
                        continue
                    set_setting(conn, k, val)
        return self._json(200, {"ok": True})

    def _upload_attachment(self, tid):
        ct = self.headers.get("Content-Type", "")
        body = self._read_body()
        if body is None:
            return self._json(413, {"error": "file too large"})
        fields, files = parse_multipart(body, ct)
        if not files:
            return self._json(400, {"error": "no file uploaded"})
        f = files[0]
        if len(f["data"]) > MAX_UPLOAD:
            return self._json(413, {"error": "file too large"})
        with _lock, db() as conn:
            if get_task(conn, tid) is None:
                return self._json(404, {"error": "task not found"})
            stored = secrets.token_hex(16)
            with open(os.path.join(ATTACH_DIR, stored), "wb") as out:
                out.write(f["data"])
            safe_name = os.path.basename(f["filename"])[:200] or "file"
            cur = conn.execute(
                "INSERT INTO attachments (task_id, filename, stored_name, size, mime) VALUES (?,?,?,?,?)",
                (tid, safe_name, stored, len(f["data"]), f["content_type"][:100]))
            log_activity(conn, tid, f"Attached {safe_name}")
            row = conn.execute("SELECT id, filename, size, mime, created_at FROM attachments WHERE id=?",
                               (cur.lastrowid,)).fetchone()
        return self._json(201, dict(row))

    def _import(self, data):
        req = ("projects", "columns", "labels", "tasks", "subtasks", "task_labels", "comments")
        if not isinstance(data, dict) or not all(isinstance(data.get(t), list) for t in req):
            return self._json(400, {"error": "invalid backup file"})
        with _lock, db() as conn:
            for t in req + ("activity", "task_deps", "time_logs", "saved_views"):
                conn.execute(f"DELETE FROM {t}")
            for r in data["projects"]:
                conn.execute("INSERT INTO projects (id, name, color, key, created_at) VALUES (?, ?, ?, ?, ?)",
                             (r.get("id"), str(r.get("name") or "?")[:100], str(r.get("color") or "#4a7dff")[:20],
                              str(r.get("key") or "")[:6] or None, r.get("created_at")))
            for r in data["columns"]:
                conn.execute("INSERT INTO columns (id, name, position, is_done, wip_limit) VALUES (?, ?, ?, ?, ?)",
                             (r.get("id"), str(r.get("name") or "?")[:60], r.get("position") or 0,
                              1 if r.get("is_done") else 0, r.get("wip_limit") or 0))
            for r in data["labels"]:
                conn.execute("INSERT INTO labels (id, name, color) VALUES (?, ?, ?)",
                             (r.get("id"), str(r.get("name") or "?")[:50], str(r.get("color") or "#7a8089")[:20]))
            for r in data["tasks"]:
                conn.execute(
                    "INSERT INTO tasks (id, title, notes, priority, due_date, project_id, column_id,"
                    " position, done, created_at, completed_at, archived, recurrence, reminder_at,"
                    " estimate_min) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (r.get("id"), str(r.get("title") or "?")[:500], str(r.get("notes") or "")[:10000],
                     r.get("priority") if r.get("priority") in PRIORITIES else "none",
                     r.get("due_date"), r.get("project_id"), r.get("column_id"), r.get("position") or 0,
                     1 if r.get("done") else 0, r.get("created_at"), r.get("completed_at"),
                     1 if r.get("archived") else 0,
                     r.get("recurrence") if r.get("recurrence") in RECURRENCE else "",
                     r.get("reminder_at"), max(0, self._int(r.get("estimate_min")) or 0)))
            for r in data["subtasks"]:
                conn.execute("INSERT INTO subtasks (id, task_id, title, done, position) VALUES (?, ?, ?, ?, ?)",
                             (r.get("id"), r.get("task_id"), str(r.get("title") or "?")[:300],
                              1 if r.get("done") else 0, r.get("position") or 0))
            for r in data["task_labels"]:
                conn.execute("INSERT OR IGNORE INTO task_labels (task_id, label_id) VALUES (?, ?)",
                             (r.get("task_id"), r.get("label_id")))
            for r in data["comments"]:
                conn.execute("INSERT INTO comments (id, task_id, body, created_at) VALUES (?, ?, ?, ?)",
                             (r.get("id"), r.get("task_id"), str(r.get("body") or "")[:5000], r.get("created_at")))
            for r in data.get("task_deps") or []:
                conn.execute("INSERT OR IGNORE INTO task_deps (task_id, depends_on_id) VALUES (?, ?)",
                             (r.get("task_id"), r.get("depends_on_id")))
            for r in data.get("time_logs") or []:
                conn.execute("INSERT INTO time_logs (id, task_id, minutes, note, created_at) VALUES (?,?,?,?,?)",
                             (r.get("id"), r.get("task_id"), self._int(r.get("minutes")) or 0,
                              str(r.get("note") or "")[:300], r.get("created_at")))
            for r in data.get("saved_views") or []:
                conn.execute("INSERT INTO saved_views (id, name, config, position) VALUES (?, ?, ?, ?)",
                             (r.get("id"), str(r.get("name") or "?")[:60],
                              json.dumps(r.get("config") if isinstance(r.get("config"), (dict, list))
                                         else r.get("config") or {})[:4000] if not isinstance(r.get("config"), str)
                              else r.get("config")[:4000], r.get("position") or 0))
            ensure_default_project(conn)
            if conn.execute("SELECT COUNT(*) c FROM columns").fetchone()["c"] == 0:
                conn.executemany("INSERT INTO columns (name, position, is_done) VALUES (?, ?, ?)",
                                 [("To Do", 0, 0), ("In Progress", 1, 0), ("Done", 2, 1)])
        self._json(200, {"ok": True})

    # ---------------- PATCH ----------------
    def do_PATCH(self):
        if not self._authed():
            return self._json(401, {"error": "auth required"})
        parts, _ = self._route()
        data = self._read_json()
        if data is None:
            return self._json(400, {"error": "invalid JSON"})
        if len(parts) != 3 or parts[0] != "api":
            return self._json(404, {"error": "not found"})
        kind, sid = parts[1], self._int(parts[2])

        if kind == "projects":
            with _lock, db() as conn:
                if not conn.execute("SELECT 1 FROM projects WHERE id=?", (sid,)).fetchone():
                    return self._json(404, {"error": "project not found"})
                if isinstance(data.get("name"), str) and data["name"].strip():
                    conn.execute("UPDATE projects SET name=? WHERE id=?", (data["name"].strip()[:100], sid))
                if isinstance(data.get("color"), str):
                    conn.execute("UPDATE projects SET color=? WHERE id=?", (data["color"][:20], sid))
                if isinstance(data.get("key"), str) and data["key"].strip():
                    conn.execute("UPDATE projects SET key=? WHERE id=?", (data["key"].strip().upper()[:6], sid))
                row = conn.execute("SELECT * FROM projects WHERE id=?", (sid,)).fetchone()
            return self._json(200, dict(row))

        if kind == "columns":
            with _lock, db() as conn:
                if not conn.execute("SELECT 1 FROM columns WHERE id=?", (sid,)).fetchone():
                    return self._json(404, {"error": "column not found"})
                if isinstance(data.get("name"), str) and data["name"].strip():
                    conn.execute("UPDATE columns SET name=? WHERE id=?", (data["name"].strip()[:60], sid))
                if "wip_limit" in data:
                    conn.execute("UPDATE columns SET wip_limit=? WHERE id=?",
                                 (max(0, self._int(data["wip_limit"]) or 0), sid))
                if "is_done" in data:
                    flag = 1 if data["is_done"] else 0
                    conn.execute("UPDATE columns SET is_done=? WHERE id=?", (flag, sid))
                    conn.execute("UPDATE tasks SET done=? WHERE column_id=?", (flag, sid))
                if "index" in data:
                    ids = [r["id"] for r in conn.execute(
                        "SELECT id FROM columns WHERE id != ? ORDER BY position", (sid,))]
                    idx = self._int(data["index"])
                    idx = len(ids) if idx is None or idx > len(ids) else max(0, idx)
                    ids.insert(idx, sid)
                    for i, cid in enumerate(ids):
                        conn.execute("UPDATE columns SET position=? WHERE id=?", (i, cid))
                row = conn.execute("SELECT * FROM columns WHERE id=?", (sid,)).fetchone()
            return self._json(200, dict(row))

        if kind == "labels":
            with _lock, db() as conn:
                if not conn.execute("SELECT 1 FROM labels WHERE id=?", (sid,)).fetchone():
                    return self._json(404, {"error": "label not found"})
                if isinstance(data.get("name"), str) and data["name"].strip():
                    conn.execute("UPDATE labels SET name=? WHERE id=?", (data["name"].strip()[:50], sid))
                if isinstance(data.get("color"), str):
                    conn.execute("UPDATE labels SET color=? WHERE id=?", (data["color"][:20], sid))
                row = conn.execute("SELECT * FROM labels WHERE id=?", (sid,)).fetchone()
            return self._json(200, dict(row))

        if kind == "subtasks":
            with _lock, db() as conn:
                if conn.execute("SELECT 1 FROM subtasks WHERE id=?", (sid,)).fetchone() is None:
                    return self._json(404, {"error": "subtask not found"})
                if isinstance(data.get("title"), str) and data["title"].strip():
                    conn.execute("UPDATE subtasks SET title=? WHERE id=?", (data["title"].strip()[:300], sid))
                if "done" in data:
                    conn.execute("UPDATE subtasks SET done=? WHERE id=?", (1 if data["done"] else 0, sid))
                row = conn.execute("SELECT * FROM subtasks WHERE id=?", (sid,)).fetchone()
            return self._json(200, dict(row))

        if kind == "saved_views":
            with _lock, db() as conn:
                if conn.execute("SELECT 1 FROM saved_views WHERE id=?", (sid,)).fetchone() is None:
                    return self._json(404, {"error": "view not found"})
                if isinstance(data.get("name"), str) and data["name"].strip():
                    conn.execute("UPDATE saved_views SET name=? WHERE id=?", (data["name"].strip()[:60], sid))
                if "config" in data:
                    conn.execute("UPDATE saved_views SET config=? WHERE id=?",
                                 (json.dumps(data["config"])[:4000], sid))
                row = conn.execute("SELECT * FROM saved_views WHERE id=?", (sid,)).fetchone()
            return self._json(200, dict(row))

        if kind == "webhooks":
            with _lock, db() as conn:
                if conn.execute("SELECT 1 FROM webhooks WHERE id=?", (sid,)).fetchone() is None:
                    return self._json(404, {"error": "webhook not found"})
                if "active" in data:
                    conn.execute("UPDATE webhooks SET active=? WHERE id=?", (1 if data["active"] else 0, sid))
                if "events" in data and isinstance(data["events"], list):
                    ev = ",".join(e for e in data["events"] if e in WEBHOOK_EVENTS)
                    conn.execute("UPDATE webhooks SET events=? WHERE id=?", (ev, sid))
                row = conn.execute("SELECT * FROM webhooks WHERE id=?", (sid,)).fetchone()
            return self._json(200, dict(row))

        if kind == "tasks":
            event = None
            with _lock, db() as conn:
                task = get_task(conn, sid)
                if task is None:
                    return self._json(404, {"error": "task not found"})
                changed = []
                if isinstance(data.get("title"), str) and data["title"].strip() and data["title"].strip() != task["title"]:
                    conn.execute("UPDATE tasks SET title=? WHERE id=?", (data["title"].strip()[:500], sid))
                    changed.append("title")
                if isinstance(data.get("notes"), str) and data["notes"] != task["notes"]:
                    conn.execute("UPDATE tasks SET notes=? WHERE id=?", (data["notes"][:10000], sid))
                    changed.append("description")
                if data.get("priority") in PRIORITIES and data["priority"] != task["priority"]:
                    conn.execute("UPDATE tasks SET priority=? WHERE id=?", (data["priority"], sid))
                    changed.append("priority")
                if "due_date" in data and (data["due_date"] or None) != task["due_date"]:
                    conn.execute("UPDATE tasks SET due_date=? WHERE id=?", (data["due_date"] or None, sid))
                    changed.append("due date")
                if "recurrence" in data and data["recurrence"] in RECURRENCE:
                    conn.execute("UPDATE tasks SET recurrence=? WHERE id=?", (data["recurrence"], sid))
                    changed.append("recurrence")
                if "reminder_at" in data:
                    conn.execute("UPDATE tasks SET reminder_at=?, reminded=0 WHERE id=?",
                                 (data["reminder_at"] or None, sid))
                    changed.append("reminder")
                if "estimate_min" in data:
                    conn.execute("UPDATE tasks SET estimate_min=? WHERE id=?",
                                 (max(0, self._int(data["estimate_min"]) or 0), sid))
                    changed.append("estimate")
                if "archived" in data:
                    conn.execute("UPDATE tasks SET archived=? WHERE id=?", (1 if data["archived"] else 0, sid))
                    changed.append("archived" if data["archived"] else "unarchived")
                if "label_ids" in data and isinstance(data["label_ids"], list):
                    conn.execute("DELETE FROM task_labels WHERE task_id=?", (sid,))
                    for lid in data["label_ids"]:
                        if conn.execute("SELECT 1 FROM labels WHERE id=?", (self._int(lid),)).fetchone():
                            conn.execute("INSERT OR IGNORE INTO task_labels (task_id, label_id) VALUES (?, ?)",
                                         (sid, self._int(lid)))
                if changed:
                    log_activity(conn, sid, "Updated " + ", ".join(changed))
                if "done" in data and "column_id" not in data:
                    col = conn.execute(
                        "SELECT id FROM columns WHERE is_done=? ORDER BY position" + (" DESC" if data["done"] else ""),
                        (1 if data["done"] else 0,)).fetchone()
                    if col:
                        data["column_id"] = col["id"]
                new_pid = None
                if "project_id" in data:
                    cand = self._int(data["project_id"])
                    if cand is not None and conn.execute("SELECT 1 FROM projects WHERE id=?", (cand,)).fetchone():
                        new_pid = cand
                if "column_id" in data or new_pid is not None or "index" in data:
                    task = get_task(conn, sid)
                    res = move_task(conn, task, self._int(data.get("column_id")), new_pid,
                                    self._int(data.get("index")))
                    if res == "completed":
                        event = "task.completed"
                row = get_task(conn, sid)
            if event == "task.completed":
                fire_event("task.completed", {"id": sid, "title": row["title"]})
            else:
                fire_event("task.updated", {"id": sid, "title": row["title"]})
            return self._json(200, task_dict(row))

        self._json(404, {"error": "not found"})

    # ---------------- DELETE ----------------
    def do_DELETE(self):
        if not self._authed():
            return self._json(401, {"error": "auth required"})
        parts, _ = self._route()
        # task dependency removal: /api/tasks/<id>/deps/<depId>
        if len(parts) == 5 and parts[:2] == ["api", "tasks"] and parts[3] == "deps":
            tid, dep = self._int(parts[2]), self._int(parts[4])
            with _lock, db() as conn:
                conn.execute("DELETE FROM task_deps WHERE task_id=? AND depends_on_id=?", (tid, dep))
            return self._send(204)
        if len(parts) != 3 or parts[0] != "api":
            return self._json(404, {"error": "not found"})
        kind, sid = parts[1], self._int(parts[2])
        with _lock, db() as conn:
            if kind == "projects":
                cur = conn.execute("DELETE FROM projects WHERE id=?", (sid,))
                if cur.rowcount == 0:
                    return self._json(404, {"error": "project not found"})
                for r in conn.execute("SELECT id FROM tasks WHERE project_id=?", (sid,)).fetchall():
                    delete_task_cascade(conn, r["id"])
                ensure_default_project(conn)
                return self._send(204)
            if kind == "columns":
                if conn.execute("SELECT COUNT(*) c FROM columns").fetchone()["c"] <= 1:
                    return self._json(400, {"error": "cannot delete the last column"})
                row = conn.execute("SELECT * FROM columns WHERE id=?", (sid,)).fetchone()
                if row is None:
                    return self._json(404, {"error": "column not found"})
                conn.execute("DELETE FROM columns WHERE id=?", (sid,))
                first = conn.execute("SELECT * FROM columns ORDER BY position LIMIT 1").fetchone()
                conn.execute("UPDATE tasks SET column_id=?, done=? WHERE column_id=?",
                             (first["id"], first["is_done"], sid))
                return self._send(204)
            if kind == "labels":
                cur = conn.execute("DELETE FROM labels WHERE id=?", (sid,))
                if cur.rowcount == 0:
                    return self._json(404, {"error": "label not found"})
                conn.execute("DELETE FROM task_labels WHERE label_id=?", (sid,))
                return self._send(204)
            if kind == "subtasks":
                cur = conn.execute("DELETE FROM subtasks WHERE id=?", (sid,))
                if cur.rowcount == 0:
                    return self._json(404, {"error": "subtask not found"})
                return self._send(204)
            if kind == "comments":
                cur = conn.execute("DELETE FROM comments WHERE id=?", (sid,))
                if cur.rowcount == 0:
                    return self._json(404, {"error": "comment not found"})
                return self._send(204)
            if kind == "time_logs":
                conn.execute("DELETE FROM time_logs WHERE id=?", (sid,))
                return self._send(204)
            if kind == "saved_views":
                conn.execute("DELETE FROM saved_views WHERE id=?", (sid,))
                return self._send(204)
            if kind == "webhooks":
                conn.execute("DELETE FROM webhooks WHERE id=?", (sid,))
                return self._send(204)
            if kind == "tokens":
                conn.execute("DELETE FROM tokens WHERE id=?", (sid,))
                return self._send(204)
            if kind == "attachments":
                row = conn.execute("SELECT stored_name FROM attachments WHERE id=?", (sid,)).fetchone()
                if row:
                    try:
                        os.remove(os.path.join(ATTACH_DIR, row["stored_name"]))
                    except OSError:
                        pass
                conn.execute("DELETE FROM attachments WHERE id=?", (sid,))
                return self._send(204)
            if kind == "tasks":
                cur = delete_task_cascade(conn, sid)
                if cur.rowcount == 0:
                    return self._json(404, {"error": "task not found"})
                fire_event("task.deleted", {"id": sid})
                return self._send(204)
        self._json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass


# HTML/JS/manifest defined after the handler (kept in separate module-level strings)
from ui import INDEX, MANIFEST, SW_JS, ICON_SVG  # noqa: E402  (local module written alongside)


def main():
    init_db()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"To-Do app v4 listening on :{PORT}, database at {DB_PATH}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
