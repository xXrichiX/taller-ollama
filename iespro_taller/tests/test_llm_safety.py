"""Tests de barrera de salida LLM."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from services.llm_safety import SAFE_REFUSAL, enforce_llm_output, is_unsafe_output


class LlmSafetyTests(unittest.TestCase):
    @patch("services.llm_safety.IS_PRODUCTION", True)
    def test_blocks_email_in_output(self) -> None:
        result = enforce_llm_output("Contacto: juan@taller.com")
        self.assertEqual(result.text, SAFE_REFUSAL)
        self.assertTrue(result.blocked)

    @patch("services.llm_safety.IS_PRODUCTION", True)
    def test_blocks_sql_leak(self) -> None:
        unsafe, reason = is_unsafe_output("SELECT * FROM usuarios WHERE id=1")
        self.assertTrue(unsafe)
        self.assertEqual(reason, "sql_leak")

    @patch("services.llm_safety.IS_PRODUCTION", True)
    def test_allows_safe_workshop_answer(self) -> None:
        result = enforce_llm_output("Hay 3 citas pendientes hoy.")
        self.assertFalse(result.blocked)
        self.assertIn("3 citas", result.text)

    @patch("services.llm_safety.IS_PRODUCTION", False)
    def test_dev_does_not_block_email(self) -> None:
        result = enforce_llm_output("Contacto: juan@taller.com")
        self.assertFalse(result.blocked)
        self.assertIn("juan@taller.com", result.text)


if __name__ == "__main__":
    unittest.main()
