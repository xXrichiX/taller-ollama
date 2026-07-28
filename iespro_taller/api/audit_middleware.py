"""Middleware de auditoría: registra accesos autenticados a la API."""

from __future__ import annotations

import logging

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.jwt_tokens import decode_session_token
from api.session import _extract_jwt
from config import SESSION_COOKIE_NAME
from services import audit_actions as audit
from services.audit_service import audit_from_request

logger = logging.getLogger(__name__)

_SKIP_PATHS = frozenset({
  "/api/health",
  "/api/auth/public-config",
  "/api/auth/captcha",
})


class AuditAccessMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next) -> Response:
    response = await call_next(request)
    path = request.url.path
    if not path.startswith("/api/") or path in _SKIP_PATHS:
      return response

    user_id: int | None = None
    try:
      cookie = request.cookies.get(SESSION_COOKIE_NAME)
      jwt_token = _extract_jwt(
        request.headers.get("Authorization"),
        request.headers.get("X-Session-Token"),
        cookie,
      )
      if jwt_token:
        claims = decode_session_token(jwt_token)
        sub = claims.get("sub")
        if sub is not None:
          user_id = int(sub)
    except (jwt.PyJWTError, TypeError, ValueError):
      pass

    try:
      audit_from_request(
        request,
        accion=audit.API_ACCESS,
        id_usuario=user_id,
        recurso=path,
        detalle=f"{request.method} {path}",
        resultado=str(response.status_code),
      )
    except Exception:
      logger.exception("Fallo audit middleware path=%s", path)

    return response
