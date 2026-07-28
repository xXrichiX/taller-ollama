"""Métricas Prometheus para observabilidad centralizada."""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from config import IS_PRODUCTION

router = APIRouter()

REQUEST_COUNT = Counter(
  "iespro_http_requests_total",
  "Total de peticiones HTTP",
  ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
  "iespro_http_request_duration_seconds",
  "Latencia de peticiones HTTP",
  ["method", "path"],
  buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
AUDIT_EVENTS = Counter(
  "iespro_audit_events_total",
  "Eventos de auditoría registrados",
  ["accion", "resultado"],
)
GUARDRAIL_BLOCKS = Counter(
  "iespro_guardrail_blocks_total",
  "Prompts bloqueados por guardrails",
  ["rule_id"],
)

_METRICS_TOKEN = os.getenv("METRICS_TOKEN", "").strip()


def record_audit_metric(accion: str, resultado: str) -> None:
  AUDIT_EVENTS.labels(accion=accion[:40], resultado=resultado[:20]).inc()


def record_guardrail_block(rule_id: str) -> None:
  GUARDRAIL_BLOCKS.labels(rule_id=rule_id[:40] or "unknown").inc()


def _authorize_metrics(request: Request) -> None:
  if not _METRICS_TOKEN:
    if IS_PRODUCTION:
      client = (request.client.host if request.client else "") or ""
      if client not in ("127.0.0.1", "::1"):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if not forwarded.startswith("127.0.0.1"):
          raise HTTPException(status_code=403, detail="Métricas no expuestas públicamente")
    return
  auth = request.headers.get("Authorization", "")
  if auth != f"Bearer {_METRICS_TOKEN}":
    raise HTTPException(status_code=403, detail="Token de métricas inválido")


@router.get("/metrics")
def prometheus_metrics(request: Request) -> Response:
  _authorize_metrics(request)
  return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


class PrometheusMiddleware:
  """Middleware ASGI ligero para contadores/latencia."""

  def __init__(self, app):
    self.app = app

  async def __call__(self, scope, receive, send):
    if scope["type"] != "http":
      await self.app(scope, receive, send)
      return

    method = scope.get("method", "GET")
    path = scope.get("path", "")
    if path == "/metrics":
      await self.app(scope, receive, send)
      return

    start = time.perf_counter()
    status_code = 500

    async def send_wrapper(message):
      nonlocal status_code
      if message["type"] == "http.response.start":
        status_code = message.get("status", 500)
      await send(message)

    await self.app(scope, receive, send_wrapper)
    elapsed = time.perf_counter() - start
    route_path = path.split("?")[0]
    if len(route_path) > 80:
      route_path = route_path[:77] + "..."
    REQUEST_COUNT.labels(method=method, path=route_path, status=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, path=route_path).observe(elapsed)
