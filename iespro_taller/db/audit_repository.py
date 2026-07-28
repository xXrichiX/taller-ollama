"""Persistencia de auditoría de seguridad."""

from __future__ import annotations

from db.connection import execute, fetch_all


class AuditRepository:
  def ensure_table(self) -> None:
    execute(
      """
      CREATE TABLE IF NOT EXISTS audit_logs (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        id_usuario INT NULL,
        accion VARCHAR(80) NOT NULL,
        recurso VARCHAR(120) NULL,
        detalle TEXT NULL,
        ip VARCHAR(45) NULL,
        user_agent VARCHAR(255) NULL,
        resultado VARCHAR(40) NOT NULL DEFAULT 'ok',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_audit_usuario (id_usuario),
        INDEX idx_audit_accion (accion),
        INDEX idx_audit_fecha (creado_en)
      )
      """
    )

  def insert(
    self,
    *,
    id_usuario: int | None,
    accion: str,
    recurso: str | None = None,
    detalle: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    resultado: str = "ok",
  ) -> None:
    execute(
      """
      INSERT INTO audit_logs (id_usuario, accion, recurso, detalle, ip, user_agent, resultado)
      VALUES (%s, %s, %s, %s, %s, %s, %s)
      """,
      (
        id_usuario,
        accion[:80],
        (recurso or "")[:120] or None,
        detalle,
        (ip or "")[:45] or None,
        (user_agent or "")[:255] or None,
        resultado[:40],
      ),
    )

  def list_recent(self, *, limit: int = 50, id_usuario: int | None = None) -> list[dict]:
    if id_usuario:
      return fetch_all(
        """
        SELECT id, id_usuario, accion, recurso, detalle, ip, user_agent, resultado, creado_en
        FROM audit_logs
        WHERE id_usuario = %s
        ORDER BY id DESC
        LIMIT %s
        """,
        (id_usuario, limit),
      )
    return fetch_all(
      """
      SELECT id, id_usuario, accion, recurso, detalle, ip, user_agent, resultado, creado_en
      FROM audit_logs
      ORDER BY id DESC
      LIMIT %s
      """,
      (limit,),
    )
