"""Frontend assets for the to-do app (kept separate from app.py for readability)."""
import json

MANIFEST = json.dumps({
    "name": "To-Do", "short_name": "To-Do", "id": "/",
    "description": "Self-hosted to-do / project board",
    "start_url": "/", "scope": "/", "display": "standalone", "orientation": "any",
    "background_color": "#16181d", "theme_color": "#4a7dff", "categories": ["productivity"],
    "icons": [
        {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        {"src": "/icon-512-rounded.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
    ],
}).encode()

ICON_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">'
    b'<rect width="192" height="192" rx="38" fill="#4a7dff"/>'
    b'<path d="M52 98l28 28 60-66" fill="none" stroke="#fff" stroke-width="16" '
    b'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)

SW_JS = b"""
const CACHE = 'todo-v5';
const SHELL = ['/', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png', '/apple-touch-icon.png'];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(
    ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api/')) return;
  e.respondWith(
    fetch(e.request).then((r) => {
      const copy = r.clone();
      caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
      return r;
    }).catch(() => caches.match(e.request).then((m) => m || caches.match('/')))
  );
});
"""

INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#4a7dff">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="To-Do">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<title>To-Do</title>
<script>try{var _t=localStorage.getItem("todo.theme");if(_t&&_t!=="system")document.documentElement.dataset.theme=_t;}catch(e){}</script>
<style>
  :root {
    color-scheme: light dark;
    --bg: #f4f5f7; --panel: #ffffff; --text: #1c1e21; --muted: #7a8089;
    --border: #e3e6ea; --hover: #eef1f5; --accent: #4a7dff; --danger: #c0392b;
    --shadow: 0 1px 3px rgba(0,0,0,.1);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #16181d; --panel: #1f2329; --text: #e4e6eb; --muted: #8a919c;
      --border: #2e333b; --hover: #262b33; --shadow: 0 1px 3px rgba(0,0,0,.45);
    }
  }
  /* ===== selectable themes (override system; chosen in Settings → Appearance) ===== */
  html[data-theme="light"] {
    color-scheme: light;
    --bg: #f4f5f7; --panel: #ffffff; --text: #1c1e21; --muted: #7a8089;
    --border: #e3e6ea; --hover: #eef1f5; --accent: #4a7dff; --danger: #c0392b;
    --shadow: 0 1px 3px rgba(0,0,0,.1);
  }
  html[data-theme="dark"] {
    color-scheme: dark;
    --bg: #16181d; --panel: #1f2329; --text: #e4e6eb; --muted: #8a919c;
    --border: #2e333b; --hover: #262b33; --accent: #4a7dff; --danger: #e06c5b;
    --shadow: 0 1px 3px rgba(0,0,0,.45);
  }
  html[data-theme="midnight"] {
    color-scheme: dark;
    --bg: #0f1226; --panel: #1a1f3d; --text: #e7e9ff; --muted: #8b91c4;
    --border: #2b3160; --hover: #232a52; --accent: #8b7bff; --danger: #ff6b8b;
    --shadow: 0 1px 3px rgba(0,0,0,.5);
  }
  html[data-theme="nord"] {
    color-scheme: dark;
    --bg: #2e3440; --panel: #3b4252; --text: #eceff4; --muted: #9aa3b5;
    --border: #434c5e; --hover: #434c5e; --accent: #88c0d0; --danger: #bf616a;
    --shadow: 0 1px 3px rgba(0,0,0,.4);
  }
  html[data-theme="solarized"] {
    color-scheme: light;
    --bg: #fdf6e3; --panel: #fffbf0; --text: #586e75; --muted: #93a1a1;
    --border: #eee8d5; --hover: #f2ecd8; --accent: #268bd2; --danger: #dc322f;
    --shadow: 0 1px 3px rgba(101,123,131,.15);
  }
  html[data-theme="forest"] {
    color-scheme: dark;
    --bg: #14201a; --panel: #1d2c24; --text: #e3efe6; --muted: #8fae9b;
    --border: #2b4034; --hover: #243730; --accent: #4cc38a; --danger: #e5715b;
    --shadow: 0 1px 3px rgba(0,0,0,.45);
  }
  html[data-theme="grape"] {
    color-scheme: dark;
    --bg: #1a1320; --panel: #271a30; --text: #f0e6f6; --muted: #b196c0;
    --border: #3b2747; --hover: #32213d; --accent: #c264fe; --danger: #ff6b8b;
    --shadow: 0 1px 3px rgba(0,0,0,.5);
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); height: 100vh; overflow: hidden;
  }
  button { font: inherit; cursor: pointer; }
  input, select, textarea {
    font: inherit; color: var(--text); background: var(--panel);
    border: 1px solid var(--border); border-radius: 8px; padding: .42rem .6rem; outline: none;
  }
  input:focus, select:focus, textarea:focus { border-color: var(--accent); }
  #app { display: flex; height: 100vh; }

  .sidebar {
    width: 240px; min-width: 240px; background: var(--panel); border-right: 1px solid var(--border);
    display: flex; flex-direction: column; padding: 1rem .75rem; gap: .25rem;
  }
  .sidebar h1 { font-size: 1.05rem; margin: 0 .25rem .5rem; }
  .add-proj { display: flex; gap: .4rem; margin-bottom: .6rem; }
  .add-proj input { flex: 1; min-width: 0; }
  .add-proj button { border: 0; border-radius: 8px; background: var(--accent); color: #fff; padding: 0 .7rem; }
  .side-label {
    font-size: .68rem; text-transform: uppercase; letter-spacing: .07em;
    color: var(--muted); margin: .5rem .35rem .25rem;
  }
  .proj-list { flex: 1; overflow-y: auto; }
  .scroll { overflow-y: auto; }
  .proj {
    display: flex; align-items: center; gap: .55rem; padding: .42rem .55rem; border-radius: 8px;
    cursor: pointer; margin-bottom: 2px; border: 0; background: none; width: 100%; text-align: left;
    color: var(--text);
  }
  .proj:hover { background: var(--hover); }
  .proj.active { background: var(--hover); font-weight: 600; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .proj .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .proj .n { font-size: .75rem; color: var(--muted); }
  .proj .x { opacity: 0; color: var(--muted); border: 0; background: none; padding: 0 .2rem; }
  .proj:hover .x { opacity: 1; }
  .side-foot { display: flex; gap: .4rem; padding-top: .5rem; border-top: 1px solid var(--border); }
  .side-foot button {
    flex: 1; border: 1px solid var(--border); background: none; color: var(--muted);
    border-radius: 8px; padding: .35rem 0; font-size: .8rem;
  }
  .side-foot button:hover { background: var(--hover); color: var(--text); }

  .main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .topbar {
    display: flex; align-items: center; gap: .6rem; padding: .75rem 1.25rem;
    border-bottom: 1px solid var(--border); background: var(--panel); flex-wrap: wrap;
  }
  .topbar h2 { margin: 0; font-size: 1.12rem; }
  .icon-btn { border: 0; background: none; color: var(--muted); border-radius: 6px; padding: .25rem .45rem; font-size: .82rem; }
  .icon-btn:hover { background: var(--hover); color: var(--text); }
  .icon-btn.danger:hover { color: var(--danger); }
  .spacer { flex: 1; }
  .views { display: flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
  .views button { border: 0; background: var(--panel); color: var(--muted); padding: .38rem .7rem; }
  .views button.active { background: var(--accent); color: #fff; }
  .topbar select { font-size: .85rem; padding: .35rem .4rem; }
  #search { width: 150px; }

  .addbar { display: flex; gap: .5rem; padding: .8rem 1.25rem 0; align-items: center; }
  .addbar input { flex: 1; }
  .addbar button { border: 0; border-radius: 8px; background: var(--accent); color: #fff; padding: .45rem 1rem; }
  .addbar .qh { font-size: .68rem; color: var(--muted); white-space: nowrap; }
  .content { flex: 1; overflow: auto; padding: 1rem 1.25rem 1.5rem; }

  .board { display: flex; gap: .9rem; align-items: flex-start; min-height: 100%; }
  .col {
    width: 280px; min-width: 280px; background: rgba(127,127,127,.07);
    border-radius: 12px; padding: .6rem; display: flex; flex-direction: column;
  }
  .col-head {
    display: flex; align-items: center; gap: .4rem; margin: .1rem .3rem .55rem;
    font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted);
  }
  .col-head .cnt { font-weight: 400; }
  .col-head .cnt.over { color: #e74c3c; font-weight: 700; }
  .col-head button { margin-left: auto; }
  .col-body { min-height: 90px; flex: 1; }
  .col-body.dragover { outline: 2px dashed var(--accent); outline-offset: -4px; border-radius: 8px; }
  .addcol {
    min-width: 200px; border: 2px dashed var(--border); background: none; border-radius: 12px;
    color: var(--muted); padding: .8rem; height: fit-content;
  }
  .addcol:hover { background: var(--hover); }
  .card {
    background: var(--panel); border-radius: 10px; box-shadow: var(--shadow); padding: .55rem .7rem;
    margin-bottom: .5rem; cursor: pointer; border-left: 3px solid transparent;
  }
  .card[draggable=true] { cursor: grab; }
  .card.p-high { border-left-color: #e74c3c; }
  .card.p-medium { border-left-color: #f39c12; }
  .card.p-low { border-left-color: #3498db; }
  .card.dragging { opacity: .4; }
  .card.blocked { opacity: .6; }
  .card .key { font-size: .68rem; color: var(--muted); letter-spacing: .03em; }
  .card .t { word-break: break-word; margin-top: .1rem; }
  .card.done .t { text-decoration: line-through; opacity: .55; }
  .meta { display: flex; gap: .45rem; flex-wrap: wrap; margin-top: .4rem; align-items: center; }
  .chip { font-size: .7rem; color: var(--muted); display: inline-flex; align-items: center; gap: .3rem; }
  .chip.overdue { color: #e74c3c; font-weight: 600; }
  .chip.block { color: #e67e22; font-weight: 600; }
  .lbl { font-size: .66rem; color: #fff; border-radius: 99px; padding: .1rem .5rem; }

  .group h3 {
    font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted);
    margin: 1.1rem .2rem .4rem;
  }
  .row {
    display: flex; align-items: center; gap: .7rem; background: var(--panel); border-radius: 10px;
    padding: .55rem .8rem; margin-bottom: .4rem; box-shadow: var(--shadow); cursor: pointer;
    border-left: 3px solid transparent;
  }
  .row.p-high { border-left-color: #e74c3c; }
  .row.p-medium { border-left-color: #f39c12; }
  .row.p-low { border-left-color: #3498db; }
  .row input[type=checkbox] { width: 1.1rem; height: 1.1rem; cursor: pointer; flex-shrink: 0; }
  .row .t { flex: 1; word-break: break-word; }
  .row.done .t { text-decoration: line-through; opacity: .55; }
  .row .key { font-size: .68rem; color: var(--muted); }
  .empty { color: var(--muted); text-align: center; padding: 2rem 0; }

  /* calendar */
  .cal-head { display: flex; align-items: center; gap: .6rem; margin-bottom: .6rem; }
  .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
  .cal-dow { font-size: .7rem; color: var(--muted); text-align: center; padding: .2rem; text-transform: uppercase; }
  .cal-cell { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; min-height: 92px; padding: .3rem; }
  .cal-cell.dim { opacity: .4; }
  .cal-cell.today { border-color: var(--accent); }
  .cal-day { font-size: .72rem; color: var(--muted); margin-bottom: .2rem; }
  .cal-ev { font-size: .68rem; background: var(--hover); border-left: 3px solid var(--accent); border-radius: 4px;
    padding: .1rem .3rem; margin-bottom: 2px; cursor: pointer; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cal-ev.done { opacity: .5; text-decoration: line-through; }
  .cal-ev.overdue { border-left-color: #e74c3c; }

  /* analytics */
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .8rem; margin-bottom: 1.2rem; }
  .stat { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 1rem; }
  .stat .num { font-size: 1.8rem; font-weight: 700; }
  .stat .lab { font-size: .75rem; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
  .panel h3 { margin: 0 0 .7rem; font-size: .95rem; }

  #colMenu {
    position: fixed; background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    box-shadow: 0 6px 20px rgba(0,0,0,.25); padding: .3rem; display: none; z-index: 20; min-width: 160px;
  }
  #colMenu button {
    display: block; width: 100%; text-align: left; border: 0; background: none; color: var(--text);
    padding: .42rem .6rem; border-radius: 6px; font-size: .85rem;
  }
  #colMenu button:hover { background: var(--hover); }
  #colMenu button.danger { color: var(--danger); }

  .overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,.45); display: none;
    align-items: flex-start; justify-content: center; z-index: 10; padding: 2rem 1rem;
  }
  .overlay.open { display: flex; }
  .modal {
    background: var(--panel); border-radius: 14px; padding: 1.25rem; width: 100%; max-width: 620px;
    box-shadow: 0 8px 30px rgba(0,0,0,.3); max-height: calc(100vh - 4rem); overflow-y: auto;
  }
  .mhead { display: flex; align-items: center; gap: .6rem; margin-bottom: .9rem; }
  .mhead .key { font-size: .75rem; color: var(--muted); white-space: nowrap; }
  .mhead input { flex: 1; font-size: 1.05rem; font-weight: 600; }
  .field { margin-bottom: .75rem; }
  .field label { display: block; font-size: .72rem; color: var(--muted); margin-bottom: .25rem; }
  .field input, .field select, .field textarea { width: 100%; }
  .field textarea { resize: vertical; min-height: 64px; }
  .grid4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: .6rem; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: .6rem; }
  .chips { display: flex; flex-wrap: wrap; gap: .35rem; margin-bottom: .4rem; }
  .chips .lbl { cursor: pointer; opacity: .35; font-size: .74rem; padding: .18rem .6rem; border: 0; }
  .chips .lbl.on { opacity: 1; }
  .inline-form { display: flex; gap: .4rem; }
  .inline-form input, .inline-form select { flex: 1; }
  .inline-form button { border: 0; border-radius: 8px; background: var(--hover); color: var(--text); padding: 0 .8rem; }
  .sub { display: flex; align-items: center; gap: .5rem; padding: .28rem 0; }
  .field .sub input[type=checkbox] { width: 1.05rem; height: 1.05rem; flex: none; cursor: pointer; }
  .sub .t { flex: 1; word-break: break-word; }
  .sub.done .t { text-decoration: line-through; opacity: .55; }
  .sub button, .com button, .att button, .dep button { border: 0; background: none; color: var(--muted); padding: .1rem .35rem; border-radius: 5px; }
  .sub button:hover, .com button:hover, .att button:hover, .dep button:hover { color: var(--danger); background: var(--hover); }
  .att, .dep, .tl { display: flex; align-items: center; gap: .5rem; padding: .25rem 0; font-size: .85rem; }
  .att a { color: var(--accent); text-decoration: none; flex: 1; word-break: break-all; }
  .att .sz, .tl .when { font-size: .68rem; color: var(--muted); }
  .dep .t { flex: 1; }
  .com { padding: .4rem 0; border-bottom: 1px solid var(--border); }
  .com:last-child { border-bottom: 0; }
  .com .when { font-size: .68rem; color: var(--muted); display: flex; gap: .4rem; align-items: center; }
  .com .body { white-space: pre-wrap; word-break: break-word; margin-top: .15rem; }
  .act { font-size: .75rem; color: var(--muted); padding: .15rem 0; }
  details summary { cursor: pointer; font-size: .8rem; color: var(--muted); margin: .5rem 0 .25rem; }
  .modal-actions { display: flex; gap: .5rem; margin-top: 1rem; align-items: center; }
  .btn { border: 0; border-radius: 8px; padding: .5rem 1rem; }
  .btn.primary { background: var(--accent); color: #fff; }
  .btn.ghost { background: var(--hover); color: var(--text); }
  .btn.danger { background: none; color: var(--danger); }
  .hint { font-size: .72rem; color: var(--muted); }
  .tabs { display: flex; gap: .3rem; margin-bottom: 1rem; flex-wrap: wrap; }
  .tabs button { border: 1px solid var(--border); background: none; color: var(--muted); border-radius: 8px; padding: .35rem .7rem; }
  .tabs button.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  .tabpane { display: none; }
  .tabpane.active { display: block; }
  code { background: var(--hover); padding: .1rem .3rem; border-radius: 4px; font-size: .85em; word-break: break-all; }

  /* login */
  #login { position: fixed; inset: 0; background: var(--bg); display: none; align-items: center; justify-content: center; z-index: 50; }
  #login.show { display: flex; }
  #login .box { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 2rem; width: 320px; max-width: 90vw; box-shadow: var(--shadow); }
  #login h2 { margin: 0 0 1rem; }
  #login input { width: 100%; margin-bottom: .8rem; }
  #login button { width: 100%; border: 0; border-radius: 8px; background: var(--accent); color: #fff; padding: .6rem; }
  #login .err { color: var(--danger); font-size: .8rem; margin-bottom: .5rem; min-height: 1rem; }

  @media (max-width: 760px) {
    .sidebar { width: 165px; min-width: 165px; }
    .board { flex-direction: column; }
    .col { width: 100%; min-width: 0; }
    .cal-cell { min-height: 64px; }
  }

  #offlineBanner {
    position: fixed; bottom: calc(14px + env(safe-area-inset-bottom)); left: 50%; transform: translateX(-50%);
    background: #e67e22; color: #fff; padding: .42rem .95rem; border-radius: 99px;
    font-size: .8rem; box-shadow: 0 2px 12px rgba(0,0,0,.35); z-index: 60; display: none; max-width: 90vw;
  }

  /* iOS standalone: keep content clear of the notch / home indicator */
  @supports (padding: env(safe-area-inset-top)) {
    .sidebar { padding-top: calc(1rem + env(safe-area-inset-top)); padding-bottom: calc(.5rem + env(safe-area-inset-bottom)); }
    .topbar { padding-top: calc(.75rem + env(safe-area-inset-top)); }
    .content { padding-bottom: calc(1.5rem + env(safe-area-inset-bottom)); }
  }
</style>
</head>
<body>
<div id="login"><div class="box">
  <h2>To-Do</h2>
  <div class="err" id="loginErr"></div>
  <input id="loginPw" type="password" placeholder="Password" autocomplete="current-password">
  <button id="loginBtn">Sign in</button>
</div></div>

<div id="app" style="display:none">
  <div class="sidebar">
    <h1>To-Do</h1>
    <form class="add-proj" id="projForm">
      <input id="projName" placeholder="New project" maxlength="100" autocomplete="off">
      <button type="submit" title="Add project">+</button>
    </form>
    <div class="side-label">Views</div>
    <div id="viewList"></div>
    <div class="side-label" id="savedLabel" style="display:none">Saved views</div>
    <div id="savedList"></div>
    <div class="side-label">Projects</div>
    <div class="proj-list" id="projList"></div>
    <div class="side-foot">
      <button id="settingsBtn" title="Settings">Settings</button>
      <button id="exportBtn" title="Download JSON backup">Export</button>
      <button id="importBtn" title="Restore from JSON backup">Import</button>
      <input type="file" id="importFile" accept="application/json" style="display:none">
    </div>
  </div>
  <div class="main">
    <div class="topbar">
      <h2 id="title">All Tasks</h2>
      <span id="projActions"></span>
      <span class="spacer"></span>
      <select id="fPrio" title="Filter by priority">
        <option value="">Priority: all</option>
        <option value="high">High</option><option value="medium">Medium</option>
        <option value="low">Low</option><option value="none">None</option>
      </select>
      <select id="fLabel" title="Filter by label"><option value="">Label: all</option></select>
      <select id="sort" title="Sort">
        <option value="manual">Sort: manual</option>
        <option value="due">Due date</option>
        <option value="priority">Priority</option>
        <option value="newest">Newest</option>
      </select>
      <input id="search" placeholder="Search...  ( / )" autocomplete="off">
      <button class="icon-btn" id="saveViewBtn" title="Save current filters as a view">Save view</button>
      <div class="views">
        <button id="vBoard">Board</button>
        <button id="vList">List</button>
        <button id="vCal">Calendar</button>
      </div>
    </div>
    <form class="addbar" id="addForm">
      <input id="addTitle" placeholder="Add a task...  ( n for details )" maxlength="500" autocomplete="off">
      <button type="submit">Add</button>
      <span class="qh">#project @label !high tomorrow every week</span>
    </form>
    <div class="content" id="content"></div>
  </div>
</div>

<div id="offlineBanner"></div>
<div id="colMenu"></div>

<!-- task modal -->
<div class="overlay" id="overlay">
  <div class="modal">
    <div class="mhead"><span class="key" id="mKey"></span><input id="fTitle" maxlength="500" placeholder="Task title"></div>
    <div class="grid4">
      <div class="field"><label>Project</label><select id="fProject"></select></div>
      <div class="field"><label>Column</label><select id="fColumn"></select></div>
      <div class="field"><label>Priority</label>
        <select id="fPriority">
          <option value="none">None</option><option value="low">Low</option>
          <option value="medium">Medium</option><option value="high">High</option>
        </select>
      </div>
      <div class="field"><label>Due date</label><input id="fDue" type="date"></div>
    </div>
    <div class="grid4">
      <div class="field"><label>Repeat</label>
        <select id="fRecur">
          <option value="">No repeat</option><option value="daily">Daily</option>
          <option value="weekdays">Weekdays</option><option value="weekly">Weekly</option>
          <option value="biweekly">Every 2 weeks</option><option value="monthly">Monthly</option>
          <option value="yearly">Yearly</option>
        </select>
      </div>
      <div class="field"><label>Reminder (UTC)</label><input id="fRemind" type="datetime-local"></div>
      <div class="field"><label>Estimate (min)</label><input id="fEstimate" type="number" min="0" step="5"></div>
      <div class="field" style="display:flex;align-items:flex-end"><span class="hint" id="loggedHint"></span></div>
    </div>
    <div class="field"><label>Description</label><textarea id="fNotes" maxlength="10000"></textarea></div>
    <div class="field"><label>Labels</label>
      <div class="chips" id="labelChips"></div>
      <form class="inline-form" id="labelForm">
        <input id="labelName" placeholder="New label" maxlength="50" autocomplete="off">
        <button type="submit">Add</button>
      </form>
    </div>
    <div id="extras">
      <div class="field"><label>Subtasks <span id="subCount"></span></label>
        <div id="subList"></div>
        <form class="inline-form" id="subForm">
          <input id="subTitle" placeholder="Add subtask" maxlength="300" autocomplete="off">
          <button type="submit">Add</button>
        </form>
      </div>
      <div class="field"><label>Dependencies (blocked by)</label>
        <div id="depList"></div>
        <form class="inline-form" id="depForm"><select id="depSelect"></select><button type="submit">Add</button></form>
      </div>
      <div class="field"><label>Attachments</label>
        <div id="attList"></div>
        <input type="file" id="attFile">
      </div>
      <div class="field"><label>Time logs <span id="tlTotal"></span></label>
        <div id="tlList"></div>
        <form class="inline-form" id="tlForm">
          <input id="tlMin" type="number" min="1" placeholder="min" style="max-width:90px">
          <input id="tlNote" placeholder="note (optional)" maxlength="300">
          <button type="submit">Log</button>
        </form>
      </div>
      <div class="field"><label>Comments</label>
        <div id="comList"></div>
        <form class="inline-form" id="comForm">
          <input id="comBody" placeholder="Write a comment" maxlength="5000" autocomplete="off">
          <button type="submit">Post</button>
        </form>
      </div>
      <details><summary>Activity</summary><div id="actList"></div></details>
    </div>
    <div class="hint" id="newHint" style="display:none">Save the task first to add subtasks, files, etc.</div>
    <div class="modal-actions">
      <button class="btn primary" id="mSave">Save</button>
      <button class="btn ghost" id="mCancel">Cancel</button>
      <button class="btn ghost" id="mArchive" style="display:none">Archive</button>
      <span class="spacer"></span>
      <button class="btn danger" id="mDelete">Delete</button>
    </div>
  </div>
</div>

<!-- settings modal -->
<div class="overlay" id="setOverlay">
  <div class="modal">
    <div class="mhead"><input id="setTitle" value="Settings" readonly style="border:0;background:none"></div>
    <div class="tabs">
      <button data-tab="notif" class="active">Notifications</button>
      <button data-tab="appearance">Appearance</button>
      <button data-tab="auth">Security</button>
      <button data-tab="hooks">Webhooks</button>
      <button data-tab="feed">Calendar feed</button>
    </div>
    <div class="tabpane" id="tab-appearance">
      <div class="field"><label>Theme</label>
        <select id="themeSel">
          <option value="system">System (match OS)</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
          <option value="midnight">Midnight</option>
          <option value="nord">Nord</option>
          <option value="solarized">Solarized</option>
          <option value="forest">Forest</option>
          <option value="grape">Grape</option>
        </select>
      </div>
      <p class="hint">Theme applies to this device (browser or desktop app) and is remembered.</p>
    </div>
    <div class="tabpane active" id="tab-notif">
      <p class="hint">Configure any channel; reminders are sent to all configured ones.</p>
      <div class="field"><label>ntfy server</label><input id="s_ntfy_url" placeholder="https://ntfy.sh"></div>
      <div class="field"><label>ntfy topic</label><input id="s_ntfy_topic" placeholder="my-todo-alerts"></div>
      <div class="grid2">
        <div class="field"><label>Telegram bot token</label><input id="s_telegram_bot_token" placeholder="leave *** to keep"></div>
        <div class="field"><label>Telegram chat ID</label><input id="s_telegram_chat_id"></div>
      </div>
      <div class="grid2">
        <div class="field"><label>SMTP host</label><input id="s_smtp_host"></div>
        <div class="field"><label>SMTP port</label><input id="s_smtp_port" placeholder="587"></div>
      </div>
      <div class="grid2">
        <div class="field"><label>SMTP user</label><input id="s_smtp_user"></div>
        <div class="field"><label>SMTP password</label><input id="s_smtp_pass" type="password" placeholder="leave *** to keep"></div>
      </div>
      <div class="grid2">
        <div class="field"><label>From address</label><input id="s_smtp_from"></div>
        <div class="field"><label>To address</label><input id="s_smtp_to"></div>
      </div>
      <div class="modal-actions">
        <button class="btn primary" id="setSave">Save</button>
        <button class="btn ghost" id="setTest">Send test</button>
        <span class="hint" id="setMsg"></span>
      </div>
    </div>
    <div class="tabpane" id="tab-auth">
      <p class="hint" id="authStatus"></p>
      <div class="field"><label>Set / change password (blank = disable login)</label>
        <input id="setPw" type="password" placeholder="New password"></div>
      <div class="modal-actions"><button class="btn primary" id="savePw">Save password</button>
        <span class="hint" id="pwMsg"></span></div>
      <hr style="border:0;border-top:1px solid var(--border);margin:1rem 0">
      <label class="side-label" style="margin:0 0 .4rem">API tokens (for scripts / agents)</label>
      <div id="tokList"></div>
      <form class="inline-form" id="tokForm" style="margin-top:.5rem">
        <input id="tokName" placeholder="Token name (e.g. my-script)"><button type="submit">Create</button>
      </form>
      <p class="hint" id="tokNew"></p>
    </div>
    <div class="tabpane" id="tab-hooks">
      <p class="hint">POST JSON to a URL when tasks change.</p>
      <div id="hookList"></div>
      <form class="inline-form" id="hookForm" style="margin-top:.5rem">
        <input id="hookUrl" placeholder="https://example.com/webhook"><button type="submit">Add</button>
      </form>
      <p class="hint">Events: task.created, task.updated, task.completed, task.deleted (all by default).</p>
    </div>
    <div class="tabpane" id="tab-feed">
      <p class="hint">Subscribe to your due dates in any calendar app (read-only):</p>
      <div class="field"><input id="feedUrl" readonly></div>
      <button class="btn ghost" id="copyFeed">Copy URL</button>
    </div>
    <div class="modal-actions"><span class="spacer"></span><button class="btn ghost" id="setClose">Close</button></div>
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);
const PALETTE = ["#4a7dff", "#27ae60", "#e67e22", "#9b59b6", "#e74c3c", "#16a085", "#f1c40f", "#e84393"];
const PRIO_RANK = { high: 0, medium: 1, low: 2, none: 3 };
const SMART = { today: "Today", upcoming: "Upcoming", overdue: "Overdue", archived: "Archived" };

const state = {
  projects: [], columns: [], labels: [], tasks: [], saved: [],
  cur: localStorage.getItem("todo.cur") || "all",
  view: localStorage.getItem("todo.view") || "board",
  q: "", fPrio: "", fLabel: "", sort: "manual",
  calMonth: null,
};
let editId = null;
let modalLabels = new Set();
let dragId = null;

/* ===== API base + offline-first sync ===== */
const API = (window.__API_BASE__ || "").replace(/\/+$/, "");
const LS = window.localStorage;
let online = true, syncing = false;
let queue = JSON.parse(LS.getItem("todo.queue") || "[]");
let tempSeq = Number(LS.getItem("todo.tempSeq") || "-1");
const persistQueue = () => { LS.setItem("todo.queue", JSON.stringify(queue)); };
const saveCache = (s) => { try { LS.setItem("todo.cache", JSON.stringify(s)); } catch (e) {} };
const loadCache = () => { try { return JSON.parse(LS.getItem("todo.cache")); } catch (e) { return null; } };
function OfflineError() { this.name = "OfflineError"; this.message = "offline"; }

function setOnline(flag) {
  const changed = flag !== online;
  online = flag; updateBanner();
  if (changed && flag) syncQueue();
}
function updateBanner() {
  const b = document.getElementById("offlineBanner"); if (!b) return;
  const n = queue.length;
  if (!online) { b.style.display = "block"; b.textContent = "Offline — changes saved here" + (n ? " (" + n + " pending)" : ""); }
  else if (n) { b.style.display = "block"; b.textContent = "Syncing " + n + " change" + (n > 1 ? "s" : "") + "…"; }
  else { b.style.display = "none"; }
}

async function apiGet(path) {
  try {
    const res = await fetch(API + path, { headers: { "Accept": "application/json" } });
    if (res.status === 401) { showLogin(); throw new Error("auth"); }
    if (!res.ok) throw new Error("Request failed");
    setOnline(true);
    return await res.json();
  } catch (e) {
    if (e instanceof TypeError) { setOnline(false); throw new OfflineError(); }
    throw e;
  }
}

// Unified entry. GETs hit the network (or throw OfflineError); mutations queue when offline.
async function api(path, opts) {
  opts = opts || {};
  const method = (opts.method || "GET").toUpperCase();
  if (method === "GET") {
    try {
      const res = await fetch(API + path, opts);
      if (res.status === 401) { showLogin(); throw new Error("auth"); }
      if (!res.ok && res.status !== 204) { let m = "Request failed"; try { m = (await res.json()).error || m; } catch (e) {} alert(m); throw new Error(m); }
      setOnline(true);
      return res.status === 204 ? null : res.json();
    } catch (e) {
      if (e instanceof TypeError) { setOnline(false); throw new OfflineError(); }
      throw e;
    }
  }
  return mutate(method, path, opts);
}

async function mutate(method, path, opts) {
  const body = opts.body ? JSON.parse(opts.body) : null;
  if (online && queue.length === 0) {
    try {
      const res = await fetch(API + path, { method, headers: opts.headers, body: opts.body });
      if (res.status === 401) { showLogin(); throw new Error("auth"); }
      if (!res.ok && res.status !== 204) { let m = "Request failed"; try { m = (await res.json()).error || m; } catch (e) {} alert(m); throw new Error(m); }
      setOnline(true);
      return res.status === 204 ? null : res.json();
    } catch (e) {
      if (!(e instanceof TypeError)) throw e;
      setOnline(false);
    }
  }
  return enqueue(method, path, body);
}

function enqueue(method, path, body) {
  const op = { method, path, body };
  let result = { ok: true };
  if (method === "POST" && (path === "/api/tasks" || path === "/api/quickadd")) {
    op.tempId = tempSeq--; LS.setItem("todo.tempSeq", String(tempSeq));
    const fields = path === "/api/quickadd" ? { title: (body && body.text) || "" } : body;
    result = synthTask(op.tempId, fields);
  }
  queue.push(op); persistQueue();
  const base = loadCache();
  if (base) { applyOp(base, op); saveCache(base); }
  updateBanner(); scheduleSync();
  return result;
}

function synthTask(id, body) {
  return Object.assign({
    id, title: "", notes: "", priority: "none", due_date: null, project_id: null,
    column_id: null, position: 9e9, archived: 0, recurrence: "", reminder_at: null,
    estimate_min: 0, completed_at: null, created_at: new Date().toISOString(),
    subtasks_total: 0, subtasks_done: 0, comments: 0, label_ids: [], attachments: 0,
    logged_min: 0, blocked_by: [],
  }, body || {});
}

function offlineDetail(id) {
  const t = taskById(id); if (!t) return null;
  return Object.assign({}, t, { subtasks: [], comments_list: [], activity: [], attachments: [],
    time_logs: [], depends_on: [], blocks: [], logged_min: t.logged_min || 0 });
}

// Mirror the essential server effects of an op onto a cached state (task CRUD only).
function applyOp(s, op) {
  if (!s || !s.tasks) return;
  const m = op.method, p = op.path, b = op.body || {};
  const doneCol = (s.columns.find(c => c.is_done) || {}).id;
  const firstCol = (s.columns[0] || {}).id;
  if (m === "POST" && (p === "/api/tasks" || p === "/api/quickadd")) {
    const fields = p === "/api/quickadd" ? { title: (b.text || "") } : b;
    const t = synthTask(op.tempId, fields);
    if (t.project_id == null) t.project_id = (s.projects[0] || {}).id;
    if (t.column_id == null) t.column_id = firstCol;
    s.tasks.push(t); return;
  }
  const mt = p.match(/^\/api\/tasks\/(-?\d+)$/);
  if (mt) {
    const id = Number(mt[1]);
    if (m === "DELETE") { s.tasks = s.tasks.filter(x => x.id !== id); return; }
    const t = s.tasks.find(x => x.id === id); if (!t) return;
    for (const k of ["title", "notes", "priority", "due_date", "recurrence", "reminder_at", "estimate_min", "label_ids"]) {
      if (k in b) t[k] = b[k];
    }
    if ("archived" in b) t.archived = b.archived ? 1 : 0;
    if ("done" in b && !("column_id" in b)) t.column_id = b.done ? doneCol : firstCol;
    if ("column_id" in b && b.column_id != null) t.column_id = b.column_id;
    if ("project_id" in b && b.project_id != null) t.project_id = b.project_id;
  }
}
function applyQueue(s) { for (const op of queue) applyOp(s, op); return s; }

async function syncQueue() {
  if (syncing || !online || !queue.length) return;
  syncing = true; updateBanner();
  const idmap = {};
  while (queue.length) {
    const op = queue[0];
    let path = op.path;
    const mt = path.match(/^\/api\/tasks\/(-?\d+)(\/.*)?$/);
    if (mt && idmap[mt[1]] != null) path = "/api/tasks/" + idmap[mt[1]] + (mt[2] || "");
    try {
      const res = await fetch(API + path, { method: op.method,
        headers: { "Content-Type": "application/json" },
        body: op.body ? JSON.stringify(op.body) : undefined });
      if (!res.ok && res.status !== 204) { queue.shift(); persistQueue(); continue; }
      const data = res.status === 204 ? null : await res.json();
      if (op.tempId && data && data.id) idmap[op.tempId] = data.id;
      queue.shift(); persistQueue(); updateBanner();
    } catch (e) {
      if (e instanceof TypeError) { setOnline(false); break; }
      queue.shift(); persistQueue();
    }
  }
  syncing = false; updateBanner();
  if (online && queue.length === 0) refresh();
}
function scheduleSync() { if (online) setTimeout(syncQueue, 50); }

window.addEventListener("online", () => setOnline(true));
window.addEventListener("offline", () => setOnline(false));
setInterval(async () => {
  if (online && !queue.length) return;
  try { const r = await fetch(API + "/healthz", { cache: "no-store" }); if (r.ok) setOnline(true); } catch (e) {}
}, 15000);

const jbody = (o) => ({ headers: { "Content-Type": "application/json" }, body: JSON.stringify(o) });
const today = () => new Date().toISOString().slice(0, 10);
const plusDays = (n) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

/* ================= auth ================= */
function showLogin() { $("login").classList.add("show"); $("app").style.display = "none"; }
$("loginBtn").onclick = async () => {
  const res = await fetch(API + "/api/login", { method: "POST", ...jbody({ password: $("loginPw").value }) });
  if (res.ok) { location.reload(); }
  else { $("loginErr").textContent = "Wrong password"; }
};
$("loginPw").addEventListener("keydown", (e) => { if (e.key === "Enter") $("loginBtn").click(); });

async function boot() {
  let me = null;
  try { me = await (await fetch(API + "/api/me")).json(); }
  catch (e) { setOnline(false); }            // offline at launch — fall back to cache
  if (me && me.auth_required && !me.authed) { showLogin(); return; }
  $("app").style.display = "flex";
  if (/^https?:$/.test(location.protocol) && "serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  refresh();
}

/* ================= data ================= */
async function refresh() {
  // Always fetch the full board (incl. archived) so the local cache is complete for offline use.
  let base;
  try {
    base = await apiGet("/api/state?archived=1");
    saveCache(base);
  } catch (e) {
    if (e && e.name === "OfflineError") {
      base = loadCache();
      if (!base) { $("content").innerHTML = '<div class="empty">Offline — open this once while the server is reachable to load your board.</div>'; updateBanner(); return; }
    } else throw e;
  }
  const view = JSON.parse(JSON.stringify(base));
  applyQueue(view);
  Object.assign(state, { projects: view.projects, columns: view.columns, labels: view.labels, tasks: view.tasks, saved: view.saved_views });
  if (!(state.cur in SMART) && state.cur !== "all" && state.cur !== "analytics" &&
      !String(state.cur).startsWith("view:") &&
      !state.projects.some(p => String(p.id) === String(state.cur))) {
    state.cur = "all"; localStorage.setItem("todo.cur", "all");
  }
  updateBanner();
  render();
  if (online && queue.length) scheduleSync();
}

const projById = (id) => state.projects.find(p => p.id === id);
const colById = (id) => state.columns.find(c => c.id === id);
const isDoneCol = (id) => { const c = colById(id); return c ? !!c.is_done : false; };
const taskById = (id) => state.tasks.find(t => t.id === id);

/* ================= sidebar ================= */
function renderSidebar() {
  const mk = (parent, id, name, color, count, onDel) => {
    const b = el("button", "proj" + (String(state.cur) === String(id) ? " active" : ""));
    b.type = "button";
    const d = el("span", "dot"); d.style.background = color;
    b.append(d, el("span", "name", name));
    if (count !== undefined && count !== null) b.append(el("span", "n", String(count)));
    if (onDel) { const x = el("button", "x", "x"); x.onclick = (e) => { e.stopPropagation(); onDel(); }; b.append(x); }
    b.onclick = () => { state.cur = String(id); localStorage.setItem("todo.cur", state.cur); refresh(); };
    parent.appendChild(b);
  };
  const vl = $("viewList"); vl.innerHTML = "";
  const totalOpen = state.projects.reduce((s, p) => s + p.open, 0);
  mk(vl, "all", "All Tasks", "var(--muted)", totalOpen);
  mk(vl, "today", "Today", "#27ae60");
  mk(vl, "upcoming", "Upcoming", "#f39c12");
  mk(vl, "overdue", "Overdue", "#e74c3c");
  mk(vl, "archived", "Archived", "#8a919c");
  mk(vl, "analytics", "Analytics", "#9b59b6");

  $("savedLabel").style.display = state.saved.length ? "" : "none";
  const sv = $("savedList"); sv.innerHTML = "";
  for (const v of state.saved) {
    const b = el("button", "proj" + (state.cur === "view:" + v.id ? " active" : "")); b.type = "button";
    const d = el("span", "dot"); d.style.background = "#16a085";
    b.append(d, el("span", "name", v.name));
    const x = el("button", "x", "x");
    x.onclick = async (e) => { e.stopPropagation();
      if (confirm('Delete saved view "' + v.name + '"?')) { await api("/api/saved_views/" + v.id, { method: "DELETE" }); refresh(); } };
    b.append(x);
    b.onclick = () => { applySavedView(v); state.cur = "view:" + v.id; localStorage.setItem("todo.cur", state.cur); refresh(); };
    sv.appendChild(b);
  }
  const pl = $("projList"); pl.innerHTML = "";
  for (const p of state.projects) mk(pl, p.id, p.name, p.color, p.open);
}

/* ================= topbar ================= */
function applySavedView(v) {
  const c = v.config || {};
  state.fPrio = c.fPrio || ""; state.fLabel = c.fLabel || ""; state.sort = c.sort || "manual";
  state.q = c.q || ""; state.view = c.view || "board";
  $("fPrio").value = state.fPrio; $("fLabel").value = state.fLabel;
  $("sort").value = state.sort; $("search").value = state.q;
}

function curProject() {
  if (state.cur in SMART || state.cur === "all" || state.cur === "analytics" || String(state.cur).startsWith("view:")) return null;
  return projById(Number(state.cur));
}

function renderTopbar() {
  const cur = curProject();
  let titleText = "All Tasks";
  if (cur) titleText = cur.name;
  else if (state.cur === "analytics") titleText = "Analytics";
  else if (String(state.cur).startsWith("view:")) {
    const v = state.saved.find(x => "view:" + x.id === state.cur);
    titleText = v ? v.name : "View";
  } else titleText = SMART[state.cur] || "All Tasks";
  $("title").textContent = titleText;
  const acts = $("projActions"); acts.innerHTML = "";
  if (cur) {
    acts.appendChild(el("span", "chip", cur.key));
    const ren = el("button", "icon-btn", "Rename");
    ren.onclick = async () => { const name = prompt("Rename project", cur.name);
      if (name && name.trim()) { await api("/api/projects/" + cur.id, { method: "PATCH", ...jbody({ name }) }); refresh(); } };
    const keyb = el("button", "icon-btn", "Key");
    keyb.onclick = async () => { const key = prompt("Project key", cur.key);
      if (key && key.trim()) { await api("/api/projects/" + cur.id, { method: "PATCH", ...jbody({ key }) }); refresh(); } };
    const del = el("button", "icon-btn danger", "Delete");
    del.onclick = async () => { if (confirm('Delete project "' + cur.name + '" and all its tasks?')) {
      await api("/api/projects/" + cur.id, { method: "DELETE" }); state.cur = "all"; localStorage.setItem("todo.cur", "all"); refresh(); } };
    acts.append(ren, keyb, del);
  }
  $("vBoard").className = state.view === "board" ? "active" : "";
  $("vList").className = state.view === "list" ? "active" : "";
  $("vCal").className = state.view === "calendar" ? "active" : "";
  const fl = $("fLabel"); const cv = fl.value;
  fl.innerHTML = '<option value="">Label: all</option>';
  for (const l of state.labels) { const o = document.createElement("option"); o.value = l.id; o.textContent = l.name; fl.appendChild(o); }
  fl.value = cv;
}

/* ================= filtering ================= */
function visible() {
  let ts = state.tasks;
  const cur = String(state.cur);
  // archived vs active (we now fetch the full board incl. archived)
  ts = (cur === "archived") ? ts.filter(t => t.archived) : ts.filter(t => !t.archived);
  // a specific project is selected
  if (/^\d+$/.test(cur)) ts = ts.filter(t => t.project_id === Number(cur));
  if (state.cur === "today") ts = ts.filter(t => t.due_date && t.due_date <= today() && !isDoneCol(t.column_id));
  if (state.cur === "upcoming") ts = ts.filter(t => t.due_date && t.due_date > today() && t.due_date <= plusDays(7) && !isDoneCol(t.column_id));
  if (state.cur === "overdue") ts = ts.filter(t => t.due_date && t.due_date < today() && !isDoneCol(t.column_id));
  if (state.fPrio) ts = ts.filter(t => t.priority === state.fPrio);
  if (state.fLabel) ts = ts.filter(t => t.label_ids.includes(Number(state.fLabel)));
  const q = state.q.toLowerCase();
  if (q) ts = ts.filter(t => (t.title + " " + t.notes).toLowerCase().includes(q));
  return ts;
}

function sortItems(items) {
  if (state.sort === "due") return [...items].sort((a, b) => (a.due_date || "9999") < (b.due_date || "9999") ? -1 : 1);
  if (state.sort === "priority") return [...items].sort((a, b) => PRIO_RANK[a.priority] - PRIO_RANK[b.priority]);
  if (state.sort === "newest") return [...items].sort((a, b) => b.id - a.id);
  return [...items].sort((a, b) => a.position - b.position);
}

/* ================= card meta ================= */
function metaRow(t) {
  const m = el("div", "meta");
  for (const lid of t.label_ids) {
    const l = state.labels.find(x => x.id === lid); if (!l) continue;
    const s = el("span", "lbl", l.name); s.style.background = l.color; m.appendChild(s);
  }
  if (t.blocked_by && t.blocked_by.length) m.appendChild(el("span", "chip block", "Blocked"));
  if (state.cur === "all" || state.cur in SMART || String(state.cur).startsWith("view:")) {
    const p = projById(t.project_id);
    if (p) { const c = el("span", "chip"); const d = el("span", "dot"); d.style.background = p.color;
      c.append(d, document.createTextNode(p.name)); m.appendChild(c); }
  }
  if (t.due_date) {
    const over = t.due_date < today() && !isDoneCol(t.column_id);
    m.appendChild(el("span", "chip" + (over ? " overdue" : ""), (over ? "Overdue " : "Due ") + t.due_date));
  }
  if (t.recurrence) m.appendChild(el("span", "chip", "Repeats " + t.recurrence));
  if (t.reminder_at) m.appendChild(el("span", "chip", "Reminder"));
  if (t.priority !== "none") m.appendChild(el("span", "chip", t.priority[0].toUpperCase() + t.priority.slice(1)));
  if (t.subtasks_total) m.appendChild(el("span", "chip", "Subtasks " + t.subtasks_done + "/" + t.subtasks_total));
  if (t.attachments) m.appendChild(el("span", "chip", t.attachments + " file" + (t.attachments > 1 ? "s" : "")));
  if (t.logged_min) m.appendChild(el("span", "chip", fmtMin(t.logged_min)));
  if (t.comments) m.appendChild(el("span", "chip", t.comments + " comment" + (t.comments > 1 ? "s" : "")));
  return m;
}
function fmtMin(m) { return m >= 60 ? (m / 60).toFixed(m % 60 ? 1 : 0) + "h" : m + "m"; }
function taskKey(t) { const p = projById(t.project_id); return (p ? p.key : "TASK") + "-" + t.id; }

/* ================= board ================= */
function renderBoard(root) {
  const board = el("div", "board");
  const tasks = visible();
  const manual = state.sort === "manual";
  for (const c of state.columns) {
    const col = el("div", "col");
    const items = sortItems(tasks.filter(t => t.column_id === c.id));
    const head = el("div", "col-head");
    const cnt = el("span", "cnt" + (c.wip_limit && items.length > c.wip_limit ? " over" : ""),
      c.wip_limit ? items.length + "/" + c.wip_limit : String(items.length));
    const menu = el("button", "icon-btn", "..."); menu.onclick = (e) => { e.stopPropagation(); openColMenu(e, c); };
    head.append(el("span", "", c.name), cnt, menu);
    const body = el("div", "col-body");
    for (const t of items) {
      const blocked = t.blocked_by && t.blocked_by.length;
      const card = el("div", "card p-" + t.priority + (isDoneCol(t.column_id) ? " done" : "") + (blocked ? " blocked" : ""));
      card.draggable = manual; card.dataset.id = t.id;
      card.append(el("div", "key", taskKey(t)), el("div", "t", t.title));
      const m = metaRow(t); if (m.childNodes.length) card.appendChild(m);
      card.onclick = () => openModal(t.id);
      if (manual) {
        card.ondragstart = (e) => { dragId = t.id; card.classList.add("dragging");
          e.dataTransfer.setData("text/plain", String(t.id)); e.dataTransfer.effectAllowed = "move"; };
        card.ondragend = () => { dragId = null; card.classList.remove("dragging"); };
      }
      body.appendChild(card);
    }
    body.ondragover = (e) => { e.preventDefault(); body.classList.add("dragover"); };
    body.ondragleave = () => body.classList.remove("dragover");
    body.ondrop = async (e) => {
      e.preventDefault(); body.classList.remove("dragover");
      const id = dragId || Number(e.dataTransfer.getData("text/plain")); if (!id) return;
      const cards = [...body.querySelectorAll(".card")].filter(x => Number(x.dataset.id) !== id);
      const index = cards.filter(x => { const r = x.getBoundingClientRect(); return r.top + r.height / 2 < e.clientY; }).length;
      await api("/api/tasks/" + id, { method: "PATCH", ...jbody({ column_id: c.id, index }) });
      refresh();
    };
    col.append(head, body); board.appendChild(col);
  }
  const add = el("button", "addcol", "+ Add column");
  add.onclick = async () => { const name = prompt("Column name");
    if (name && name.trim()) { await api("/api/columns", { method: "POST", ...jbody({ name }) }); refresh(); } };
  board.appendChild(add); root.appendChild(board);
}

/* ================= column menu ================= */
function openColMenu(e, c) {
  const menu = $("colMenu"); menu.innerHTML = "";
  const item = (label, fn, cls) => { const b = el("button", cls || "", label);
    b.onclick = async () => { menu.style.display = "none"; await fn(); }; menu.appendChild(b); };
  item("Rename", async () => { const name = prompt("Column name", c.name);
    if (name && name.trim()) { await api("/api/columns/" + c.id, { method: "PATCH", ...jbody({ name }) }); refresh(); } });
  item("WIP limit" + (c.wip_limit ? " (" + c.wip_limit + ")" : ""), async () => {
    const v = prompt("WIP limit (0 = none)", String(c.wip_limit));
    if (v !== null) { await api("/api/columns/" + c.id, { method: "PATCH", ...jbody({ wip_limit: Number(v) || 0 }) }); refresh(); } });
  const idx = state.columns.findIndex(x => x.id === c.id);
  if (idx > 0) item("Move left", async () => { await api("/api/columns/" + c.id, { method: "PATCH", ...jbody({ index: idx - 1 }) }); refresh(); });
  if (idx < state.columns.length - 1) item("Move right", async () => { await api("/api/columns/" + c.id, { method: "PATCH", ...jbody({ index: idx + 1 }) }); refresh(); });
  item(c.is_done ? "Unmark as Done column" : "Mark as Done column", async () => {
    await api("/api/columns/" + c.id, { method: "PATCH", ...jbody({ is_done: !c.is_done }) }); refresh(); });
  item("Delete column", async () => { if (confirm('Delete column "' + c.name + '"? Its tasks move to the first column.')) {
    await api("/api/columns/" + c.id, { method: "DELETE" }); refresh(); } }, "danger");
  menu.style.display = "block";
  const r = e.target.getBoundingClientRect();
  menu.style.left = Math.min(r.left, window.innerWidth - 180) + "px";
  menu.style.top = (r.bottom + 4) + "px";
}
document.addEventListener("click", () => { $("colMenu").style.display = "none"; });

/* ================= list ================= */
function renderList(root) {
  const tasks = visible(); let any = false;
  const order = state.cur === "archived" ? [{ id: null, name: "Archived" }] : state.columns;
  for (const c of order) {
    const items = sortItems(c.id === null ? tasks : tasks.filter(t => t.column_id === c.id));
    if (!items.length) continue; any = true;
    const g = el("div", "group"); g.appendChild(el("h3", "", c.name + " (" + items.length + ")"));
    for (const t of items) {
      const row = el("div", "row p-" + t.priority + (isDoneCol(t.column_id) ? " done" : ""));
      const cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = isDoneCol(t.column_id);
      cb.onclick = async (e) => { e.stopPropagation(); await api("/api/tasks/" + t.id, { method: "PATCH", ...jbody({ done: cb.checked }) }); refresh(); };
      row.append(cb, el("span", "key", taskKey(t)), el("span", "t", t.title));
      const m = metaRow(t); if (m.childNodes.length) row.appendChild(m);
      row.onclick = () => openModal(t.id); g.appendChild(row);
    }
    root.appendChild(g);
  }
  if (!any) root.appendChild(el("div", "empty", "Nothing here. Add a task above."));
}

/* ================= calendar ================= */
function renderCalendar(root) {
  const ref = state.calMonth ? new Date(state.calMonth) : new Date();
  const year = ref.getFullYear(), month = ref.getMonth();
  const head = el("div", "cal-head");
  const prev = el("button", "icon-btn", "< Prev"); const next = el("button", "icon-btn", "Next >");
  const tdy = el("button", "icon-btn", "Today");
  prev.onclick = () => { state.calMonth = new Date(year, month - 1, 1).toISOString(); render(); };
  next.onclick = () => { state.calMonth = new Date(year, month + 1, 1).toISOString(); render(); };
  tdy.onclick = () => { state.calMonth = null; render(); };
  head.append(prev, el("strong", "", ref.toLocaleString(undefined, { month: "long", year: "numeric" })), next, tdy);
  root.appendChild(head);
  const grid = el("div", "cal-grid");
  for (const d of ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]) grid.appendChild(el("div", "cal-dow", d));
  const first = new Date(year, month, 1); const start = new Date(first); start.setDate(1 - first.getDay());
  const byDate = {};
  for (const t of visible()) { if (t.due_date) (byDate[t.due_date] = byDate[t.due_date] || []).push(t); }
  for (let i = 0; i < 42; i++) {
    const day = new Date(start); day.setDate(start.getDate() + i);
    const iso = day.toISOString().slice(0, 10);
    const cell = el("div", "cal-cell" + (day.getMonth() !== month ? " dim" : "") + (iso === today() ? " today" : ""));
    cell.appendChild(el("div", "cal-day", String(day.getDate())));
    for (const t of (byDate[iso] || [])) {
      const over = iso < today() && !isDoneCol(t.column_id);
      const ev = el("div", "cal-ev" + (isDoneCol(t.column_id) ? " done" : "") + (over ? " overdue" : ""), t.title);
      ev.onclick = () => openModal(t.id); cell.appendChild(ev);
    }
    grid.appendChild(cell);
  }
  root.appendChild(grid);
}

/* ================= analytics ================= */
async function renderAnalytics(root) {
  root.appendChild(el("div", "hint", "Loading..."));
  let s;
  try { s = await api("/api/stats"); }
  catch (e) { if (e && e.name === "OfflineError") { root.innerHTML = ""; root.appendChild(el("div", "empty", "Analytics needs a connection to the server.")); return; } throw e; }
  root.innerHTML = "";
  const stats = el("div", "stats");
  const card = (num, lab) => { const d = el("div", "stat"); d.append(el("div", "num", String(num)), el("div", "lab", lab)); return d; };
  stats.append(card(s.totals.open, "Open"), card(s.totals.done, "Completed"),
    card(s.totals.overdue, "Overdue"), card(s.totals.archived, "Archived"), card(fmtMin(s.logged_min), "Time logged"));
  root.appendChild(stats);

  const p1 = el("div", "panel"); p1.appendChild(el("h3", "", "Created vs completed (last 8 weeks)"));
  p1.appendChild(barChart(s.weeks.map(w => ({ label: w.week.slice(5), a: w.created, b: w.completed }))));
  p1.appendChild(legend()); root.appendChild(p1);

  const p2 = el("div", "panel"); p2.appendChild(el("h3", "", "Open tasks by priority"));
  const pr = s.by_priority;
  p2.appendChild(simpleBars([["High", pr.high, "#e74c3c"], ["Medium", pr.medium, "#f39c12"],
    ["Low", pr.low, "#3498db"], ["None", pr.none, "#7a8089"]])); root.appendChild(p2);

  const p3 = el("div", "panel"); p3.appendChild(el("h3", "", "Tasks by column"));
  p3.appendChild(simpleBars(s.by_column.map(c => [c.name, c.count, c.is_done ? "#27ae60" : "#4a7dff"]))); root.appendChild(p3);
}
function legend() { const d = el("div", "hint"); d.innerHTML = '<span style="color:#4a7dff">&#9632;</span> created &nbsp; <span style="color:#27ae60">&#9632;</span> completed'; return d; }
function barChart(data) {
  const W = Math.max(320, data.length * 64), H = 180, pad = 24;
  const max = Math.max(1, ...data.map(d => Math.max(d.a, d.b)));
  const bw = (W - pad * 2) / data.length;
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg"); svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.style.width = "100%"; svg.style.maxHeight = "200px";
  data.forEach((d, i) => {
    const x = pad + i * bw;
    const ha = (H - pad * 2) * d.a / max, hb = (H - pad * 2) * d.b / max;
    const r1 = document.createElementNS(ns, "rect");
    r1.setAttribute("x", x + 6); r1.setAttribute("y", H - pad - ha); r1.setAttribute("width", bw / 2 - 8); r1.setAttribute("height", ha); r1.setAttribute("fill", "#4a7dff"); r1.setAttribute("rx", 2);
    const r2 = document.createElementNS(ns, "rect");
    r2.setAttribute("x", x + bw / 2); r2.setAttribute("y", H - pad - hb); r2.setAttribute("width", bw / 2 - 8); r2.setAttribute("height", hb); r2.setAttribute("fill", "#27ae60"); r2.setAttribute("rx", 2);
    const tx = document.createElementNS(ns, "text"); tx.setAttribute("x", x + bw / 2); tx.setAttribute("y", H - 6);
    tx.setAttribute("text-anchor", "middle"); tx.setAttribute("font-size", "9"); tx.setAttribute("fill", "currentColor"); tx.textContent = d.label;
    svg.append(r1, r2, tx);
  });
  return svg;
}
function simpleBars(rows) {
  const max = Math.max(1, ...rows.map(r => r[1])); const wrap = el("div");
  for (const [label, val, color] of rows) {
    const line = el("div"); line.style.display = "flex"; line.style.alignItems = "center"; line.style.gap = ".5rem"; line.style.margin = ".25rem 0";
    const lab = el("span", "", label); lab.style.width = "110px"; lab.style.fontSize = ".8rem";
    const track = el("div"); track.style.flex = "1"; track.style.background = "var(--hover)"; track.style.borderRadius = "5px"; track.style.height = "16px";
    const bar = el("div"); bar.style.width = (100 * val / max) + "%"; bar.style.background = color; bar.style.height = "100%"; bar.style.borderRadius = "5px";
    track.appendChild(bar); const num = el("span", "", String(val)); num.style.width = "32px"; num.style.fontSize = ".8rem"; num.style.textAlign = "right";
    line.append(lab, track, num); wrap.appendChild(line);
  }
  return wrap;
}

/* ================= render ================= */
function render() {
  renderSidebar(); renderTopbar();
  const root = $("content"); root.innerHTML = "";
  if (state.cur === "analytics") { renderAnalytics(root); return; }
  if (state.view === "calendar") renderCalendar(root);
  else if (state.view === "board" && state.cur !== "archived") renderBoard(root);
  else renderList(root);
}

/* ================= modal ================= */
function fillSelect(sel, items, selected) {
  sel.innerHTML = "";
  for (const it of items) { const o = document.createElement("option"); o.value = it.id; o.textContent = it.name; if (it.id === selected) o.selected = true; sel.appendChild(o); }
}
function renderLabelChips() {
  const box = $("labelChips"); box.innerHTML = "";
  if (!state.labels.length) box.appendChild(el("span", "hint", "No labels yet - add one below."));
  for (const l of state.labels) {
    const b = el("button", "lbl" + (modalLabels.has(l.id) ? " on" : ""), l.name); b.type = "button"; b.style.background = l.color;
    b.onclick = () => { modalLabels.has(l.id) ? modalLabels.delete(l.id) : modalLabels.add(l.id); renderLabelChips(); };
    box.appendChild(b);
  }
}
function renderDetail(d) {
  $("subCount").textContent = d.subtasks.length ? "(" + d.subtasks.filter(s => s.done).length + "/" + d.subtasks.length + ")" : "";
  const sl = $("subList"); sl.innerHTML = "";
  for (const s of d.subtasks) {
    const row = el("div", "sub" + (s.done ? " done" : ""));
    const cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = !!s.done;
    cb.onchange = async () => { await api("/api/subtasks/" + s.id, { method: "PATCH", ...jbody({ done: cb.checked }) }); reloadDetail(); };
    const x = el("button", "", "x"); x.onclick = async () => { await api("/api/subtasks/" + s.id, { method: "DELETE" }); reloadDetail(); };
    row.append(cb, el("span", "t", s.title), x); sl.appendChild(row);
  }
  // dependencies
  const dl = $("depList"); dl.innerHTML = "";
  for (const id of d.depends_on) {
    const t = taskById(id); const row = el("div", "dep");
    row.append(el("span", "t", t ? (taskKey(t) + " " + t.title) : ("task " + id)));
    const x = el("button", "", "x"); x.onclick = async () => { await api("/api/tasks/" + d.id + "/deps/" + id, { method: "DELETE" }); reloadDetail(); };
    row.append(x); dl.appendChild(row);
  }
  const ds = $("depSelect"); ds.innerHTML = '<option value="">Pick a task it depends on...</option>';
  for (const t of state.tasks) { if (t.id === d.id || d.depends_on.includes(t.id)) continue;
    const o = document.createElement("option"); o.value = t.id; o.textContent = taskKey(t) + " " + t.title.slice(0, 40); ds.appendChild(o); }
  // attachments
  const al = $("attList"); al.innerHTML = "";
  for (const a of d.attachments) {
    const row = el("div", "att");
    const link = el("a", "", a.filename); link.href = "/api/attachments/" + a.id;
    row.append(link, el("span", "sz", fmtSize(a.size)));
    const x = el("button", "", "x"); x.onclick = async () => { await api("/api/attachments/" + a.id, { method: "DELETE" }); reloadDetail(); };
    row.append(x); al.appendChild(row);
  }
  // time logs
  const total = d.logged_min || 0;
  $("tlTotal").textContent = total ? "(" + fmtMin(total) + (d.estimate_min ? " / " + fmtMin(d.estimate_min) + " est" : "") + ")" : "";
  $("loggedHint").textContent = total ? "Logged " + fmtMin(total) : "";
  const tll = $("tlList"); tll.innerHTML = "";
  for (const l of d.time_logs) {
    const row = el("div", "tl");
    row.append(el("span", "", fmtMin(l.minutes) + (l.note ? " - " + l.note : "")), el("span", "when", l.created_at + " UTC"));
    const x = el("button", "", "x"); x.onclick = async () => { await api("/api/time_logs/" + l.id, { method: "DELETE" }); reloadDetail(); };
    row.append(x); tll.appendChild(row);
  }
  // comments + activity
  const cl = $("comList"); cl.innerHTML = "";
  for (const cm of d.comments_list) {
    const c = el("div", "com"); const when = el("div", "when", cm.created_at + " UTC");
    const x = el("button", "", "x"); x.onclick = async () => { await api("/api/comments/" + cm.id, { method: "DELETE" }); reloadDetail(); };
    when.appendChild(x); c.append(when, el("div", "body", cm.body)); cl.appendChild(c);
  }
  const acl = $("actList"); acl.innerHTML = "";
  for (const a of d.activity) acl.appendChild(el("div", "act", a.created_at + " - " + a.text));
}
function fmtSize(b) { return b >= 1048576 ? (b / 1048576).toFixed(1) + " MB" : (b / 1024).toFixed(0) + " KB"; }
async function reloadDetail() {
  if (!editId) return;
  try { renderDetail(await api("/api/tasks/" + editId)); }
  catch (e) { if (!(e && e.name === "OfflineError")) throw e; renderDetail(offlineDetail(editId)); }
}

async function openModal(taskId) {
  editId = taskId || null; modalLabels = new Set();
  let t = null;
  if (editId) {
    try { t = await api("/api/tasks/" + editId); }
    catch (e) { if (e && e.name === "OfflineError") t = offlineDetail(editId); else throw e; }
  }
  $("mKey").textContent = t ? taskKey(t) : "NEW";
  $("fTitle").value = t ? t.title : "";
  $("fNotes").value = t ? t.notes : "";
  $("fPriority").value = t ? t.priority : "none";
  $("fDue").value = t && t.due_date ? t.due_date : "";
  $("fRecur").value = t && t.recurrence ? t.recurrence : "";
  $("fRemind").value = t && t.reminder_at ? t.reminder_at.replace(" ", "T").slice(0, 16) : "";
  $("fEstimate").value = t && t.estimate_min ? t.estimate_min : "";
  const defaultPid = curProject() ? curProject().id : (state.projects[0] || {}).id;
  fillSelect($("fProject"), state.projects, t ? t.project_id : defaultPid);
  fillSelect($("fColumn"), state.columns, t ? t.column_id : (state.columns[0] || {}).id);
  if (t) for (const lid of t.label_ids) modalLabels.add(lid);
  renderLabelChips();
  $("extras").style.display = t ? "" : "none";
  $("newHint").style.display = t ? "none" : "";
  $("mDelete").style.display = t ? "" : "none";
  $("mArchive").style.display = t ? "" : "none";
  $("mArchive").textContent = t && t.archived ? "Unarchive" : "Archive";
  if (t) renderDetail(t);
  $("overlay").classList.add("open"); $("fTitle").focus();
}
function closeModal() { $("overlay").classList.remove("open"); editId = null; }

$("mSave").onclick = async () => {
  const payload = {
    title: $("fTitle").value.trim(), notes: $("fNotes").value, priority: $("fPriority").value,
    due_date: $("fDue").value || null, project_id: Number($("fProject").value), column_id: Number($("fColumn").value),
    label_ids: [...modalLabels], recurrence: $("fRecur").value,
    reminder_at: $("fRemind").value ? $("fRemind").value.replace("T", " ") + ":00" : null,
    estimate_min: Number($("fEstimate").value) || 0,
  };
  if (!payload.title) { alert("Title is required"); return; }
  if (editId) await api("/api/tasks/" + editId, { method: "PATCH", ...jbody(payload) });
  else await api("/api/tasks", { method: "POST", ...jbody(payload) });
  closeModal(); refresh();
};
$("mCancel").onclick = closeModal;
$("mArchive").onclick = async () => {
  if (!editId) return;
  const t = taskById(editId); const arch = !(t && t.archived);
  await api("/api/tasks/" + editId, { method: "PATCH", ...jbody({ archived: arch }) });
  closeModal(); refresh();
};
$("mDelete").onclick = async () => { if (editId && confirm("Delete this task?")) {
  await api("/api/tasks/" + editId, { method: "DELETE" }); closeModal(); refresh(); } };
$("overlay").onclick = (e) => { if (e.target === $("overlay")) closeModal(); };

$("labelForm").onsubmit = async (e) => {
  e.preventDefault(); const name = $("labelName").value.trim(); if (!name) return;
  const color = PALETTE[(state.labels.length + 3) % PALETTE.length];
  const l = await api("/api/labels", { method: "POST", ...jbody({ name, color }) });
  if (!state.labels.some(x => x.id === l.id)) state.labels.push(l);
  modalLabels.add(l.id); $("labelName").value = ""; renderLabelChips();
};
$("subForm").onsubmit = async (e) => {
  e.preventDefault(); const title = $("subTitle").value.trim(); if (!title || !editId) return;
  await api("/api/tasks/" + editId + "/subtasks", { method: "POST", ...jbody({ title }) });
  $("subTitle").value = ""; reloadDetail();
};
$("depForm").onsubmit = async (e) => {
  e.preventDefault(); const dep = Number($("depSelect").value); if (!dep || !editId) return;
  await api("/api/tasks/" + editId + "/deps", { method: "POST", ...jbody({ depends_on_id: dep }) });
  reloadDetail(); refresh();
};
$("attFile").onchange = async () => {
  const f = $("attFile").files[0]; if (!f || !editId) return;
  if (!online) { alert("Attachments need a connection — try again when back online."); $("attFile").value = ""; return; }
  const fd = new FormData(); fd.append("file", f);
  try {
    const res = await fetch(API + "/api/tasks/" + editId + "/attachments", { method: "POST", body: fd });
    if (!res.ok) alert("Upload failed");
  } catch (e) { setOnline(false); alert("Attachments need a connection — try again when back online."); }
  $("attFile").value = ""; reloadDetail(); refresh();
};
$("tlForm").onsubmit = async (e) => {
  e.preventDefault(); const min = Number($("tlMin").value); if (!min || !editId) return;
  await api("/api/tasks/" + editId + "/timelogs", { method: "POST", ...jbody({ minutes: min, note: $("tlNote").value }) });
  $("tlMin").value = ""; $("tlNote").value = ""; reloadDetail(); refresh();
};
$("comForm").onsubmit = async (e) => {
  e.preventDefault(); const body = $("comBody").value.trim(); if (!body || !editId) return;
  await api("/api/tasks/" + editId + "/comments", { method: "POST", ...jbody({ body }) });
  $("comBody").value = ""; reloadDetail();
};

/* ================= top-level ================= */
$("addForm").onsubmit = async (e) => {
  e.preventDefault(); const text = $("addTitle").value.trim(); if (!text) return;
  // Online: server parses #project @label !prio dates. Offline: shows the raw title now,
  // then gets parsed by the server when the queued quickadd syncs.
  await api("/api/quickadd", { method: "POST", ...jbody({ text }) });
  $("addTitle").value = ""; refresh();
};
$("projForm").onsubmit = async (e) => {
  e.preventDefault(); const name = $("projName").value.trim(); if (!name) return;
  const color = PALETTE[state.projects.length % PALETTE.length];
  const p = await api("/api/projects", { method: "POST", ...jbody({ name, color }) });
  $("projName").value = ""; state.cur = String(p.id); localStorage.setItem("todo.cur", state.cur); refresh();
};
$("vBoard").onclick = () => { state.view = "board"; localStorage.setItem("todo.view", "board"); render(); };
$("vList").onclick = () => { state.view = "list"; localStorage.setItem("todo.view", "list"); render(); };
$("vCal").onclick = () => { state.view = "calendar"; localStorage.setItem("todo.view", "calendar"); render(); };
$("search").oninput = () => { state.q = $("search").value; render(); };
$("fPrio").onchange = () => { state.fPrio = $("fPrio").value; render(); };
$("fLabel").onchange = () => { state.fLabel = $("fLabel").value; render(); };
$("sort").onchange = () => { state.sort = $("sort").value; render(); };
$("saveViewBtn").onclick = async () => {
  const name = prompt("Name this view"); if (!name || !name.trim()) return;
  const config = { fPrio: state.fPrio, fLabel: state.fLabel, sort: state.sort, q: state.q, view: state.view };
  await api("/api/saved_views", { method: "POST", ...jbody({ name, config }) }); refresh();
};

$("exportBtn").onclick = async () => {
  const data = await api("/api/export");
  const blob = new Blob([JSON.stringify(data, null, 1)], { type: "application/json" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "todo-backup-" + today() + ".json"; a.click(); URL.revokeObjectURL(a.href);
};
$("importBtn").onclick = () => $("importFile").click();
$("importFile").onchange = async () => {
  const f = $("importFile").files[0]; if (!f) return;
  if (!confirm("Importing replaces ALL current data. Continue?")) { $("importFile").value = ""; return; }
  try { const data = JSON.parse(await f.text()); await api("/api/import", { method: "POST", ...jbody(data) }); state.cur = "all"; refresh(); }
  catch (err) { alert("Import failed: " + err.message); }
  $("importFile").value = "";
};

/* ================= settings ================= */
const NOTIF_FIELDS = ["ntfy_url", "ntfy_topic", "telegram_bot_token", "telegram_chat_id", "smtp_host", "smtp_port", "smtp_user", "smtp_pass", "smtp_from", "smtp_to"];
function setTheme(t) {
  if (!t || t === "system") { delete document.documentElement.dataset.theme; localStorage.setItem("todo.theme", "system"); }
  else { document.documentElement.dataset.theme = t; localStorage.setItem("todo.theme", t); }
}
async function openSettings() {
  $("themeSel").value = localStorage.getItem("todo.theme") || "system";
  $("setOverlay").classList.add("open");
  try {
    const cfg = await api("/api/settings");          // notification/auth settings live on the server
    for (const k of NOTIF_FIELDS) { const e = $("s_" + k); if (e) e.value = cfg[k] || ""; }
    $("authStatus").textContent = cfg.has_password ? "Login is ON. Blank the field below to disable it." : "Login is OFF — the app is open on your network.";
    $("feedUrl").value = (API || location.origin) + "/ical?token=" + cfg.feed_token;
    await loadTokens(); await loadHooks();
  } catch (e) {
    if (!(e && e.name === "OfflineError")) throw e;
    $("authStatus").textContent = "Offline — server settings unavailable. Theme still works.";
  }
}
$("themeSel").onchange = () => setTheme($("themeSel").value);
$("settingsBtn").onclick = openSettings;
$("setClose").onclick = () => $("setOverlay").classList.remove("open");
$("setOverlay").onclick = (e) => { if (e.target === $("setOverlay")) $("setOverlay").classList.remove("open"); };
for (const b of document.querySelectorAll(".tabs button")) b.onclick = () => {
  document.querySelectorAll(".tabs button").forEach(x => x.classList.remove("active"));
  document.querySelectorAll(".tabpane").forEach(x => x.classList.remove("active"));
  b.classList.add("active"); $("tab-" + b.dataset.tab).classList.add("active");
};
$("setSave").onclick = async () => {
  const body = {}; for (const k of NOTIF_FIELDS) body[k] = $("s_" + k).value;
  await api("/api/settings", { method: "POST", ...jbody(body) }); $("setMsg").textContent = "Saved.";
  setTimeout(() => $("setMsg").textContent = "", 2000);
};
$("setTest").onclick = async () => {
  $("setMsg").textContent = "Sending...";
  const r = await api("/api/notify-test", { method: "POST", ...jbody({}) });
  $("setMsg").textContent = Object.entries(r).map(([k, v]) => k + ": " + v).join("  •  ");
};
$("savePw").onclick = async () => {
  await api("/api/settings", { method: "POST", ...jbody({ password: $("setPw").value }) });
  $("pwMsg").textContent = $("setPw").value ? "Login enabled." : "Login disabled."; $("setPw").value = "";
};
async function loadTokens() {
  const toks = await api("/api/tokens"); const box = $("tokList"); box.innerHTML = "";
  if (!toks.length) box.appendChild(el("span", "hint", "No tokens yet."));
  for (const t of toks) {
    const row = el("div", "att");
    row.append(el("span", "t", t.name + "  (" + t.preview + ")  " + (t.last_used ? "used " + t.last_used : "never used")));
    const x = el("button", "", "Revoke"); x.onclick = async () => { await api("/api/tokens/" + t.id, { method: "DELETE" }); loadTokens(); };
    row.append(x); box.appendChild(row);
  }
}
$("tokForm").onsubmit = async (e) => {
  e.preventDefault(); const name = $("tokName").value.trim() || "API token";
  const r = await api("/api/tokens", { method: "POST", ...jbody({ name }) });
  $("tokNew").textContent = "New token (copy now, shown once): " + r.token; $("tokName").value = ""; loadTokens();
};
async function loadHooks() {
  const hooks = await api("/api/webhooks"); const box = $("hookList"); box.innerHTML = "";
  if (!hooks.length) box.appendChild(el("span", "hint", "No webhooks yet."));
  for (const h of hooks) {
    const row = el("div", "att");
    row.append(el("span", "t", h.url + (h.active ? "" : " (disabled)")));
    const x = el("button", "", "Delete"); x.onclick = async () => { await api("/api/webhooks/" + h.id, { method: "DELETE" }); loadHooks(); };
    row.append(x); box.appendChild(row);
  }
}
$("hookForm").onsubmit = async (e) => {
  e.preventDefault(); const url = $("hookUrl").value.trim(); if (!url) return;
  await api("/api/webhooks", { method: "POST", ...jbody({ url, events: [] }) }); $("hookUrl").value = ""; loadHooks();
};
$("copyFeed").onclick = () => { navigator.clipboard.writeText($("feedUrl").value).then(() => { $("copyFeed").textContent = "Copied!"; setTimeout(() => $("copyFeed").textContent = "Copy URL", 1500); }); };

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closeModal(); $("setOverlay").classList.remove("open"); return; }
  const tag = (document.activeElement || {}).tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
  if (e.key === "n") { e.preventDefault(); openModal(null); }
  if (e.key === "/") { e.preventDefault(); $("search").focus(); }
  if (e.key === "b") { state.view = "board"; localStorage.setItem("todo.view", "board"); render(); }
  if (e.key === "l") { state.view = "list"; localStorage.setItem("todo.view", "list"); render(); }
  if (e.key === "c") { state.view = "calendar"; localStorage.setItem("todo.view", "calendar"); render(); }
});

boot();
</script>
</body>
</html>
"""

INDEX = INDEX_HTML.encode("utf-8")
