"""Persistencia de auditoría de seguridad."""

from __future__ import annotations

from config import AUDIT_RETENTION_DAYS
from db.connection import execute, fetch_all
from services.audit_integrity import compute_integrity_hash, verify_integrity_hash


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
        integrity_hash CHAR(64) NULL,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_audit_usuario (id_usuario),
        INDEX idx_audit_accion (accion),
        INDEX idx_audit_fecha (creado_en)
      )
      """
    )
    col = fetch_all(
      """
      SELECT COUNT(*) AS n FROM information_schema.columns
      WHERE table_schema = DATABASE() AND table_name = 'audit_logs'
        AND column_name = 'integrity_hash'
      """
    )
    if col and col[0].get("n", 0) == 0:
      execute("ALTER TABLE audit_logs ADD COLUMN integrity_hash CHAR(64) NULL AFTER resultado")

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
    integrity_hash = compute_integrity_hash(
      id_usuario=id_usuario,
      accion=accion[:80],
      recurso=(recurso or "")[:120] or None,
      detalle=detalle,
      ip=(ip or "")[:45] or None,
      user_agent=(user_agent or "")[:255] or None,
      resultado=resultado[:40],
    )
    execute(
      """
      INSERT INTO audit_logs (
        id_usuario, accion, recurso, detalle, ip, user_agent, resultado, integrity_hash
      )
      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
      """,
      (
        id_usuario,
        accion[:80],
        (recurso or "")[:120] or None,
        detalle,
        (ip or "")[:45] or None,
        (user_agent or "")[:255] or None,
        resultado[:40],
        integrity_hash,
      ),
    )

  def list_recent(self, *, limit: int = 50, id_usuario: int | None = None) -> list[dict]:
    if id_usuario:
      return fetch_all(
        """
        SELECT id, id_usuario, accion, recurso, detalle, ip, user_agent, resultado,
               integrity_hash, creado_en
        FROM audit_logs
        WHERE id_usuario = %s
        ORDER BY id DESC
        LIMIT %s
        """,
        (id_usuario, limit),
      )
    return fetch_all(
      """
      SELECT id, id_usuario, accion, recurso, detalle, ip, user_agent, resultado,
             integrity_hash, creado_en
      FROM audit_logs
      ORDER BY id DESC
      LIMIT %s
      """,
      (limit,),
    )

  def verify_recent(self, *, limit: int = 200) -> dict:
    rows = self.list_recent(limit=limit)
    checked = 0
    invalid_ids: list[int] = []
    missing_hash_ids: list[int] = []
    for row in rows:
      rid = int(row["id"])
      if not row.get("integrity_hash"):
        missing_hash_ids.append(rid)
        continue
      checked += 1
      if not verify_integrity_hash(row):
        invalid_ids.append(rid)
    return {
      "checked": checked,
      "invalid_count": len(invalid_ids),
      "invalid_ids": invalid_ids[:20],
      "missing_hash_count": len(missing_hash_ids),
      "ok": len(invalid_ids) == 0,
    }

  def purge_older_than_retention(self) -> int:
    if AUDIT_RETENTION_DAYS <= 0:
      return 0
    from db.connection import get_connection

    conn = get_connection()
    try:
      with conn.cursor() as cur:
        cur.execute(
          """
          DELETE FROM audit_logs
          WHERE creado_en < DATE_SUB(NOW(), INTERVAL %s DAY)
          """,
          (AUDIT_RETENTION_DAYS,),
        )
        deleted = cur.rowcount or 0
      conn.commit()
      return int(deleted)
    finally:
      conn.close()
