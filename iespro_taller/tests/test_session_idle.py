"""Tests de expiración de sesión por inactividad."""

from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

from api.session import create_session, get_session, purge_expired_sessions


class SessionIdleTests(unittest.TestCase):
  def _user(self) -> dict:
    return {
      "id": 1,
      "nombre": "Test",
      "email": "t@example.com",
      "rol_nombre": "MECANICO",
      "sucursales_ids": [1],
    }

  @patch("api.session.apply_user_to_session")
  @patch("api.session.issue_session_token", return_value=("jwt-test", "jti-test"))
  def test_session_expires_after_idle(self, _jwt: MagicMock, _apply: MagicMock) -> None:
    with patch("api.session.SESSION_IDLE_SECONDS", 1):
      session, _ = create_session(self._user())
      token = session.token
      self.assertIsNotNone(get_session(token))
      time.sleep(1.1)
      purge_expired_sessions()
      self.assertIsNone(get_session(token))

  @patch("api.session.apply_user_to_session")
  @patch("api.session.issue_session_token", return_value=("jwt-test", "jti-test"))
  def test_activity_refreshes_idle_timer(self, _jwt: MagicMock, _apply: MagicMock) -> None:
    with patch("api.session.SESSION_IDLE_SECONDS", 2):
      session, _ = create_session(self._user())
      token = session.token
      time.sleep(1)
      session.touch()
      time.sleep(1.2)
      self.assertIsNotNone(get_session(token))


if __name__ == "__main__":
  unittest.main()
