"""Tests de integridad HMAC en audit_logs."""

from __future__ import annotations

import unittest

from services.audit_integrity import compute_integrity_hash, verify_integrity_hash


class AuditIntegrityTests(unittest.TestCase):
  def test_hash_is_stable(self) -> None:
    kwargs = dict(
      id_usuario=1,
      accion="auth.login",
      recurso="session",
      detalle="ok",
      ip="127.0.0.1",
      user_agent="test",
      resultado="ok",
    )
    h1 = compute_integrity_hash(**kwargs)
    h2 = compute_integrity_hash(**kwargs)
    self.assertEqual(h1, h2)
    self.assertEqual(len(h1), 64)

  def test_tamper_detection(self) -> None:
    row = {
      "id_usuario": 1,
      "accion": "auth.login",
      "recurso": "session",
      "detalle": "ok",
      "ip": "127.0.0.1",
      "user_agent": "test",
      "resultado": "ok",
      "integrity_hash": compute_integrity_hash(
        id_usuario=1,
        accion="auth.login",
        recurso="session",
        detalle="ok",
        ip="127.0.0.1",
        user_agent="test",
        resultado="ok",
      ),
    }
    self.assertTrue(verify_integrity_hash(row))
    row["detalle"] = "tampered"
    self.assertFalse(verify_integrity_hash(row))


if __name__ == "__main__":
  unittest.main()
