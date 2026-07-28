"""Tests de acceso a citas (IDOR)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from api.access_checks import assert_cita_access
from api.session import AppSession


class AccessChecksTests(unittest.TestCase):
  def _session(self, *, rol: str = "CLIENTE", uid: int = 1, id_cliente: int = 10) -> AppSession:
    chat = MagicMock()
    return AppSession(
      token="t",
      user={"id": uid, "rol_nombre": rol},
      id_sucursal=1,
      id_cliente=id_cliente,
      chat=chat,
    )

  def test_cliente_cannot_view_foreign_cita(self) -> None:
    session = self._session()
    cita = {"id": 1, "id_cliente": 99, "id_sucursal": 1}
    with self.assertRaises(HTTPException) as ctx:
      assert_cita_access(session, cita)
    self.assertEqual(ctx.exception.status_code, 403)

  @patch("api.access_checks.catalog_service.user_is_propietario", return_value=False)
  def test_mecanico_only_assigned_citas(self, _mock: MagicMock) -> None:
    session = self._session(rol="MECANICO", uid=5, id_cliente=None)
    cita = {"id": 1, "id_mecanico": 99, "id_sucursal": 1}
    with self.assertRaises(HTTPException) as ctx:
      assert_cita_access(session, cita)
    self.assertEqual(ctx.exception.status_code, 403)

  @patch("api.access_checks.catalog_service.list_usuarios", return_value=[{"id": 2}])
  @patch("api.access_checks.require_sucursal", return_value=1)
  def test_assert_usuario_in_workshop_ok(self, _sid: MagicMock, _list: MagicMock) -> None:
    from api.access_checks import assert_usuario_in_workshop

    session = self._session(rol="PROPIETARIO", uid=1)
    session.id_sucursal = 1
    assert_usuario_in_workshop(session, 2)

  @patch("api.access_checks.catalog_service.list_usuarios", return_value=[{"id": 2}])
  @patch("api.access_checks.require_sucursal", return_value=1)
  def test_assert_usuario_in_workshop_foreign(self, _sid: MagicMock, _list: MagicMock) -> None:
    from api.access_checks import assert_usuario_in_workshop

    session = self._session(rol="PROPIETARIO", uid=1)
    session.id_sucursal = 1
    with self.assertRaises(HTTPException) as ctx:
      assert_usuario_in_workshop(session, 99)
    self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
  unittest.main()
