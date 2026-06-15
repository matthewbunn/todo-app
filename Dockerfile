FROM python:3.12-alpine

WORKDIR /app
COPY app.py ui.py icons.json ./

ENV DB_PATH=/data/todo.db \
    PORT=8080 \
    ATTACH_DIR=/data/attachments

VOLUME ["/data"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1

CMD ["python", "app.py"]
