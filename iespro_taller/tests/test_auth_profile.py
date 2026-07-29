"""Tests de perfil de cuenta (auth/me sin permissions en prod)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from api.auth_profile import account_profile, account_ui


class AuthProfileTests(unittest.TestCase):
  def test_owner_profile(self) -> None:
    session = MagicMock()
    session.user = {"id": 1, "rol_nombre": "MECANICO"}
    with patch("api.auth_profile.is_cliente", return_value=False), patch(
      "api.auth_profile.catalog_service.user_is_propietario",
      return_value=True,
    ):
      self.assertEqual(account_profile(session), "owner")

  def test_ui_flags(self) -> None:
    session = MagicMock()
    session.user = {"id": 1, "rol_nombre": "MECANICO"}
    session.id_sucursal = 2
    with patch(
      "api.auth_profile.catalog_service.user_is_propietario",
      return_value=True,
    ), patch(
      "api.auth_profile.catalog_service.user_needs_taller_setup",
      return_value=False,
    ), patch(
      "api.auth_profile.catalog_service.user_can_create_sucursal",
      return_value=True,
    ), patch(
      "api.auth_profile.cita_service.list_islas",
      return_value=[{"id": 1}, {"id": 2}],
    ), patch(
      "api.auth_profile.is_workshop_staff",
      return_value=True,
    ):
      ui = account_ui(session)
      self.assertTrue(ui["isla_picker"])
      self.assertTrue(ui["can_add_branch"])


if __name__ == "__main__":
  unittest.main()
