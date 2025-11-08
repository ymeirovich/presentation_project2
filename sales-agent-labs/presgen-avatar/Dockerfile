FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8002

COPY presgen-avatar/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY presgen-avatar/app ./app
COPY presgen-avatar/assets ./assets

EXPOSE 8002

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8002}"]
