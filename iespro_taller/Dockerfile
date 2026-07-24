# Backend IESPRO-Taller — multi-stage build
FROM python:3.12-slim AS builder
WORKDIR /app
COPY iespro_taller/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/iespro_taller

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY iespro_taller /app/iespro_taller

WORKDIR /app/iespro_taller
EXPOSE 8000

# Ollama corre en el host; el contenedor se conecta vía host.docker.internal
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
