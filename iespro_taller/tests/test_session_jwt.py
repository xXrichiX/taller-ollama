"""Tests de validación de claims JWT en sesión."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from api.session import _session_from_jwt


class SessionJwtClaimsTests(unittest.TestCase):
  @patch("api.session.get_session")
  @patch("api.session.decode_session_token")
  def test_rejects_rol_mismatch(self, decode: MagicMock, get_session: MagicMock) -> None:
    decode.return_value = {
      "sub": "1",
      "jti": "abc",
      "rol": "CLIENTE",
    }
    session = MagicMock()
    session.user = {"id": 1, "rol_nombre": "MECANICO"}
    get_session.return_value = session

    self.assertIsNone(_session_from_jwt("token"))

  @patch("api.session.get_session")
  @patch("api.session.decode_session_token")
  def test_accepts_matching_rol(self, decode: MagicMock, get_session: MagicMock) -> None:
    decode.return_value = {
      "sub": "1",
      "jti": "abc",
      "rol": "MECANICO",
    }
    session = MagicMock()
    session.user = {"id": 1, "rol_nombre": "MECANICO"}
    get_session.return_value = session

    self.assertIs(session, _session_from_jwt("token"))


if __name__ == "__main__":
  unittest.main()
