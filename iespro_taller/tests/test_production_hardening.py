"""Controles de endurecimiento para producción."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from api.observability_public import public_observability_logs
from api.production_checks import validate_production_config


class ProductionHardeningTests(unittest.TestCase):
  def test_observability_redacts_long_prompts(self) -> None:
    rows = [
      {
        "user_prompt": "x" * 200,
        "system_response": "y" * 200,
        "tools_executed": [{"name": "crear_cita", "args": {"secret": 1}}],
      }
    ]
    out = public_observability_logs(rows)
    self.assertIn("redactado", out[0]["user_prompt"])
    self.assertIn("redactado", out[0]["system_response"])
    self.assertEqual(out[0]["tools_executed"], [{"name": "crear_cita"}])

  @patch("api.production_checks.IS_PRODUCTION", True)
  @patch("api.production_checks.SESSION_STORE", "memory")
  @patch("api.production_checks.MYSQL_PASSWORD", "x" * 20)
  @patch("api.production_checks.MYSQL_USER", "iespro_app")
  @patch("api.production_checks.AUDIT_HMAC_SECRET", "a" * 32)
  @patch("api.production_checks.METRICS_TOKEN", "m" * 32)
  @patch("api.production_checks.REGISTRATION_ENABLED", False)
  def test_production_requires_mysql_session_store(self) -> None:
    with self.assertRaises(RuntimeError) as ctx:
      validate_production_config()
    self.assertIn("SESSION_STORE", str(ctx.exception))


if __name__ == "__main__":
  unittest.main()
