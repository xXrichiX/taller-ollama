"""Cookie HttpOnly para sesión (anti-XSS)."""

from __future__ import annotations

from fastapi import Response
from fastapi.responses import JSONResponse

from config import SESSION_COOKIE_MAX_AGE, SESSION_COOKIE_NAME, SESSION_COOKIE_SECURE

COOKIE_PATH = "/"


def attach_session_cookie(response: Response, jwt_token: str) -> None:
  response.set_cookie(
    key=SESSION_COOKIE_NAME,
    value=jwt_token,
    httponly=True,
    secure=SESSION_COOKIE_SECURE,
    samesite="strict",
    max_age=SESSION_COOKIE_MAX_AGE,
    path=COOKIE_PATH,
  )


def clear_session_cookie(response: Response) -> None:
  response.delete_cookie(
    key=SESSION_COOKIE_NAME,
    path=COOKIE_PATH,
    httponly=True,
    secure=SESSION_COOKIE_SECURE,
    samesite="strict",
  )


def json_with_session(payload: dict, jwt_token: str, status_code: int = 200) -> JSONResponse:
  response = JSONResponse(content=payload, status_code=status_code)
  attach_session_cookie(response, jwt_token)
  return response
