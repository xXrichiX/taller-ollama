"""WAF edge: el manifiesto nginx debe estar presente en el repo."""

from __future__ import annotations

import unittest

from security.nginx_waf import REQUIRED_WAF_MARKERS, verify_nginx_waf_config


class NginxWafTests(unittest.TestCase):
  def test_waf_manifest_complete(self) -> None:
    report = verify_nginx_waf_config()
    self.assertTrue(report["implemented"], f"Faltan: {report.get('missing_markers')}")
    self.assertGreaterEqual(report["required_markers"], len(REQUIRED_WAF_MARKERS))

  def test_blocks_sensitive_paths_in_config(self) -> None:
    features = verify_nginx_waf_config()["features"]
    self.assertTrue(features["sensitive_paths_404"])
    self.assertTrue(features["bot_block"])
    self.assertTrue(features["rate_limit_chat"])


if __name__ == "__main__":
  unittest.main()
