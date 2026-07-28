"""Persistencia de sesiones API en MySQL (producción)."""

from __future__ import annotations

import json
import time
from typing import Any

from db.connection import execute, fetch_all, fetch_one


def ensure_session_table() -> None:
  execute(
    """
    CREATE TABLE IF NOT EXISTS api_sessions (
      jti VARCHAR(64) PRIMARY KEY,
      id_usuario INT NOT NULL,
      id_sucursal INT NULL,
      id_isla INT NULL,
      id_cliente INT NULL,
      created_at DOUBLE NOT NULL,
      last_activity DOUBLE NOT NULL,
      INDEX idx_api_sessions_user (id_usuario),
      INDEX idx_api_sessions_activity (last_activity)
    )
    """
  )


def save_session(
  *,
  jti: str,
  id_usuario: int,
  id_sucursal: int | None,
  id_isla: int | None,
  id_cliente: int | None,
  created_at: float,
  last_activity: float,
) -> None:
  ensure_session_table()
  execute(
    """
    INSERT INTO api_sessions (
      jti, id_usuario, id_sucursal, id_isla, id_cliente, created_at, last_activity
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      id_sucursal = VALUES(id_sucursal),
      id_isla = VALUES(id_isla),
      id_cliente = VALUES(id_cliente),
      last_activity = VALUES(last_activity)
    """,
    (jti, id_usuario, id_sucursal, id_isla, id_cliente, created_at, last_activity),
  )


def load_session(jti: str) -> dict[str, Any] | None:
  ensure_session_table()
  return fetch_one(
    """
    SELECT jti, id_usuario, id_sucursal, id_isla, id_cliente, created_at, last_activity
    FROM api_sessions
    WHERE jti = %s
    """,
    (jti,),
  )


def delete_session(jti: str) -> None:
  ensure_session_table()
  execute("DELETE FROM api_sessions WHERE jti = %s", (jti,))


def purge_expired_sessions(idle_seconds: int) -> None:
  ensure_session_table()
  cutoff = time.time() - idle_seconds
  execute("DELETE FROM api_sessions WHERE last_activity < %s", (cutoff,))


def touch_session(jti: str, last_activity: float) -> None:
  ensure_session_table()
  execute(
    "UPDATE api_sessions SET last_activity = %s WHERE jti = %s",
    (last_activity, jti),
  )
