"""Códigos de invitación para registro de usuarios."""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any

from db.connection import execute, fetch_all, fetch_one


def _normalize_codigo(codigo: str) -> str:
    return (codigo or "").strip().upper()


def validar_codigo(codigo: str) -> dict[str, Any]:
    codigo = _normalize_codigo(codigo)
    if not codigo:
        return {"ok": False, "error": "Indica el código de invitación."}

    row = fetch_one(
        """
        SELECT c.*, s.nombre AS sucursal_nombre
        FROM codigos_invitacion c
        JOIN sucursales s ON s.id = c.id_sucursal
        WHERE UPPER(c.codigo) = %s AND c.activo = 1 AND s.activo = 1
        """,
        (codigo,),
    )
    if not row:
        return {"ok": False, "error": "Código de invitación no válido o inactivo."}

    if row.get("expira_en"):
        expira = row["expira_en"]
        if isinstance(expira, datetime) and expira < datetime.now():
            return {"ok": False, "error": "Este código de invitación ya expiró."}

    usos_max = int(row.get("usos_maximos") or 0)
    usos_act = int(row.get("usos_actuales") or 0)
    if usos_max > 0 and usos_act >= usos_max:
        return {"ok": False, "error": "Este código de invitación ya alcanzó su límite de usos."}

    return {
        "ok": True,
        "codigo": row["codigo"],
        "id_codigo": row["id"],
        "id_sucursal": row["id_sucursal"],
        "sucursal_nombre": row["sucursal_nombre"],
    }


def consumir_codigo(id_codigo: int) -> None:
    execute(
        "UPDATE codigos_invitacion SET usos_actuales = usos_actuales + 1 WHERE id = %s",
        (id_codigo,),
    )


def list_codigos(id_sucursal: int | None = None) -> list[dict]:
    query = """
        SELECT c.id, c.codigo, c.id_sucursal, s.nombre AS sucursal,
               c.usos_maximos, c.usos_actuales, c.expira_en, c.activo,
               c.permite_admin_sucursal, c.creado_en
        FROM codigos_invitacion c
        JOIN sucursales s ON s.id = c.id_sucursal
        WHERE 1=1
    """
    params: list[Any] = []
    if id_sucursal:
        query += " AND c.id_sucursal = %s"
        params.append(id_sucursal)
    query += " ORDER BY c.id DESC"
    return fetch_all(query, tuple(params))


def generar_codigo_aleatorio() -> str:
    """Código corto aleatorio para invitación (reintenta si ya existe)."""
    for _ in range(8):
        codigo = secrets.token_hex(4).upper()
        if not fetch_one("SELECT id FROM codigos_invitacion WHERE UPPER(codigo) = %s", (codigo,)):
            return codigo
    return secrets.token_hex(6).upper()


def crear_codigo(
    id_sucursal: int,
    *,
    codigo: str | None = None,
    usos_maximos: int = 1,
    expira_en: str | None = None,
    creado_por: int | None = None,
    permite_admin_sucursal: bool = False,
) -> dict[str, Any]:
    codigo = _normalize_codigo(codigo or secrets.token_hex(4).upper())
    if fetch_one("SELECT id FROM codigos_invitacion WHERE UPPER(codigo) = %s", (codigo,)):
        return {"ok": False, "error": "Ese código ya existe. Elige otro."}

    id_codigo = execute(
        """
        INSERT INTO codigos_invitacion
            (codigo, id_sucursal, usos_maximos, expira_en, creado_por, permite_admin_sucursal)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (codigo, id_sucursal, usos_maximos, expira_en, creado_por, int(permite_admin_sucursal)),
    )
    return {"ok": True, "id": id_codigo, "codigo": codigo}


def desactivar_codigo(id_codigo: int) -> dict[str, Any]:
    execute("UPDATE codigos_invitacion SET activo = 0 WHERE id = %s", (id_codigo,))
    return {"ok": True}
