"""Tests de scope del chat (anti-IDOR)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from api.chat_scope import apply_chat_scope
from api.session import AppSession
from services.chat_service import ChatService


class ChatScopeTests(unittest.TestCase):
  def _session(self, user_id: int = 1) -> AppSession:
    chat = ChatService()
    return AppSession(token="t", user={"id": user_id}, chat=chat)

  @patch("api.chat_scope.catalog_service.user_can_access_sucursal", return_value=False)
  def test_rejects_foreign_sucursal(self, _mock: MagicMock) -> None:
    session = self._session()
    session.id_sucursal = 1
    with self.assertRaises(HTTPException) as ctx:
      apply_chat_scope(session, id_sucursal=99, id_isla=None)
    self.assertEqual(ctx.exception.status_code, 403)

  @patch("api.chat_scope.catalog_service.user_can_access_sucursal", return_value=True)
  def test_allows_owned_sucursal(self, _mock: MagicMock) -> None:
    session = self._session()
    apply_chat_scope(session, id_sucursal=5, id_isla=None)
    self.assertEqual(session.id_sucursal, 5)
    self.assertEqual(session.chat.id_sucursal, 5)


if __name__ == "__main__":
  unittest.main()
