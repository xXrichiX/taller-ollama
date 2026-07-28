"""Tests de extracción de IP detrás de proxy."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from api.client_ip import get_client_ip


class ClientIpTests(unittest.TestCase):
  def _request(
    self,
    *,
    client_host: str = "10.0.0.5",
    headers: dict[str, str] | None = None,
  ):
    req = MagicMock()
    req.client = MagicMock(host=client_host)
    req.headers = headers or {}
    return req

  @patch("api.client_ip.TRUST_PROXY_HEADERS", False)
  def test_uses_socket_ip_without_proxy_trust(self) -> None:
    ip = get_client_ip(self._request(client_host="203.0.113.9"))
    self.assertEqual(ip, "203.0.113.9")

  @patch("api.client_ip.TRUST_PROXY_HEADERS", True)
  def test_uses_forwarded_for_when_trusted(self) -> None:
    ip = get_client_ip(
      self._request(
        client_host="10.0.0.5",
        headers={"X-Forwarded-For": "198.51.100.42, 10.0.0.5"},
      )
    )
    self.assertEqual(ip, "198.51.100.42")


if __name__ == "__main__":
  unittest.main()
