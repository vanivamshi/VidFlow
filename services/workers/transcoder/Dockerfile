FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY services/workers/transcoder/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared /app/shared
COPY services/workers/transcoder/worker.py /app/worker.py

ENV PYTHONPATH=/app
CMD ["python", "worker.py"]
