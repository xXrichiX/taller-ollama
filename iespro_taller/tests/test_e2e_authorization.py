"""Tests E2E de autorización API (roles y endpoints protegidos)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app
from api.session import AppSession, require_session
from services.chat_service import ChatService


def _session(
  *,
  rol: str,
  uid: int = 1,
  id_sucursal: int | None = 1,
) -> AppSession:
  chat = ChatService()
  return AppSession(
    token="test-jti",
    user={
      "id": uid,
      "nombre": "Test",
      "email": "test@example.com",
      "rol_nombre": rol,
      "sucursales_ids": [1] if id_sucursal else [],
    },
    id_sucursal=id_sucursal,
    id_isla=1,
    chat=chat,
  )


@patch("api.main.init_database", return_value=(True, "ok"))
class E2EAuthorizationTests(unittest.TestCase):
  def setUp(self) -> None:
    self.client = TestClient(app)
    app.dependency_overrides.clear()

  def tearDown(self) -> None:
    app.dependency_overrides.clear()

  def test_unauthenticated_audit_returns_401(self, _init: MagicMock) -> None:
    response = self.client.get("/api/audit/recent")
    self.assertEqual(response.status_code, 401)

  @patch("api.rest_routes.catalog_service.user_is_propietario", return_value=False)
  def test_cliente_cannot_read_audit(self, _owner: MagicMock, _init: MagicMock) -> None:
    app.dependency_overrides[require_session] = lambda: _session(rol="CLIENTE")
    response = self.client.get("/api/audit/recent")
    self.assertEqual(response.status_code, 403)

  @patch("api.rest_routes.catalog_service.user_is_propietario", return_value=True)
  @patch("db.audit_repository.AuditRepository.list_recent", return_value=[])
  @patch("db.audit_repository.AuditRepository.ensure_table")
  def test_propietario_can_read_audit(
    self,
    _ensure: MagicMock,
    _list: MagicMock,
    _owner: MagicMock,
    _init: MagicMock,
  ) -> None:
    app.dependency_overrides[require_session] = lambda: _session(rol="PROPIETARIO")
    response = self.client.get("/api/audit/recent")
    self.assertEqual(response.status_code, 200)
    self.assertIn("logs", response.json())

  @patch("api.rest_routes.catalog_service.user_is_propietario", return_value=False)
  def test_mecanico_cannot_bootstrap_rag(self, _owner: MagicMock, _init: MagicMock) -> None:
    app.dependency_overrides[require_session] = lambda: _session(rol="MECANICO")
    response = self.client.post("/api/rag/bootstrap")
    self.assertEqual(response.status_code, 403)

  @patch("api.rest_routes.catalog_service.user_is_propietario", return_value=True)
  def test_propietario_can_access_observability(self, _owner: MagicMock, _init: MagicMock) -> None:
    app.dependency_overrides[require_session] = lambda: _session(rol="PROPIETARIO")
    with patch("db.observability_repository.ObservabilityRepository.list_recent", return_value=[]):
      with patch("db.observability_repository.ObservabilityRepository.ensure_table"):
        response = self.client.get("/api/observability/recent")
    self.assertEqual(response.status_code, 200)

  def test_chat_conversations_requires_sucursal(self, _init: MagicMock) -> None:
    app.dependency_overrides[require_session] = lambda: _session(rol="MECANICO", id_sucursal=None)
    response = self.client.get("/api/chat/conversations")
    self.assertEqual(response.status_code, 400)

  @patch("api.rest_routes.catalog_service.user_is_propietario", return_value=True)
  @patch("db.audit_repository.AuditRepository.verify_recent", return_value={"checked": 1, "invalid_count": 0, "invalid_ids": [], "missing_hash_count": 0, "ok": True})
  @patch("db.audit_repository.AuditRepository.ensure_table")
  def test_propietario_can_verify_audit_integrity(
    self,
    _ensure: MagicMock,
    _verify: MagicMock,
    _owner: MagicMock,
    _init: MagicMock,
  ) -> None:
    app.dependency_overrides[require_session] = lambda: _session(rol="PROPIETARIO")
    response = self.client.get("/api/audit/verify")
    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.json()["ok"])

  def test_register_rejects_unknown_fields(self, _init: MagicMock) -> None:
    response = self.client.post(
      "/api/auth/register",
      json={
        "nombre": "Test",
        "email": "strict@test.com",
        "password": "Test1234!",
        "role": "ADMIN",
      },
    )
    self.assertEqual(response.status_code, 422)

  def test_login_rejects_unknown_fields(self, _init: MagicMock) -> None:
    response = self.client.post(
      "/api/auth/login",
      json={
        "email": "test@example.com",
        "password": "secret",
        "role": "ADMIN",
      },
    )
    self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
  unittest.main()
