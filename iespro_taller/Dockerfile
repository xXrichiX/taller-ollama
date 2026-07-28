# Backend IESPRO-Taller — multi-stage build
FROM python:3.12-slim AS builder
WORKDIR /app
COPY iespro_taller/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/iespro_taller
ENV VOSK_MODEL_PATH=/models/vosk-model-small-es-0.42

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 ffmpeg curl unzip \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /models \
    && curl -fsSL -o /tmp/vosk-es.zip https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip \
    && unzip -q /tmp/vosk-es.zip -d /models \
    && rm /tmp/vosk-es.zip

COPY --from=builder /install /usr/local
COPY iespro_taller /app/iespro_taller
COPY web/nginx.conf /app/web/nginx.conf

WORKDIR /app/iespro_taller
EXPOSE 8000

# Ollama corre en el host; el contenedor se conecta vía host.docker.internal
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
