"""Tests de validación de configuración en producción."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch


class ProductionChecksTests(unittest.TestCase):
  @patch.dict(os.environ, {"APP_ENV": "production"}, clear=False)
  @patch("api.production_checks.MYSQL_PASSWORD", "a" * 20)
  @patch("api.production_checks.MYSQL_USER", "iespro_app")
  @patch("api.production_checks.TRUST_PROXY_HEADERS", True)
  @patch("api.production_checks.SESSION_IDLE_SECONDS", 86400)
  @patch("api.production_checks.MAX_TOOL_CALLS_PER_TURN", 8)
  @patch("api.production_checks.AUDIT_HMAC_SECRET", "a" * 40)
  @patch("api.production_checks.METRICS_TOKEN", "b" * 40)
  @patch("api.production_checks.REGISTRATION_ENABLED", False)
  @patch("api.production_checks.IS_PRODUCTION", True)
  @patch("api.production_checks.APP_ENV", "production")
  @patch("pathlib.Path.is_file", return_value=True)
  def test_valid_production_config_passes(self, _mock_key: object) -> None:
    from api.production_checks import validate_production_config

    validate_production_config()

  @patch("api.production_checks.IS_PRODUCTION", True)
  @patch("api.production_checks.APP_ENV", "development")
  def test_rejects_non_production_app_env(self) -> None:
    from api.production_checks import validate_production_config

    with self.assertRaises(RuntimeError) as ctx:
      validate_production_config()
    self.assertIn("APP_ENV", str(ctx.exception))


if __name__ == "__main__":
  unittest.main()
