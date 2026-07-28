"""Postura de seguridad exportada por la API."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from api.security_posture import collect_security_controls


class SecurityPostureTests(unittest.TestCase):
  @patch("api.security_posture.IS_PRODUCTION", True)
  @patch("api.security_posture.AUDIT_HMAC_SECRET", "test-secret")
  @patch("api.security_posture.METRICS_TOKEN", "metrics-token")
  @patch("api.security_posture.REGISTRATION_ENABLED", False)
  def test_production_posture_compliant(self) -> None:
    data = collect_security_controls()
    self.assertEqual(data["environment"], "production")
    self.assertTrue(data["checks"]["waf_edge"])
    self.assertTrue(data["checks"]["llm_sql_disabled"])
    self.assertTrue(data["compliant"])

  @patch("api.security_posture.REGISTRATION_ENABLED", True)
  @patch("api.security_posture.TURNSTILE_SECRET_KEY", "")
  @patch("api.security_posture.TURNSTILE_SITE_KEY", "")
  @patch("api.security_posture.IS_PRODUCTION", True)
  def test_open_registration_without_turnstile_fails_check(self) -> None:
    data = collect_security_controls()
    self.assertFalse(data["registration"]["secure_for_production"])
    self.assertFalse(data["checks"]["registration_hardened"])


if __name__ == "__main__":
  unittest.main()
