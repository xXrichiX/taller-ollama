"""Tests de política de tools del asistente."""

from __future__ import annotations

import unittest

from services.tool_policy import is_tool_allowed, redact_tool_result, tools_for_session
from services.tools_service import TOOL_DEFINITIONS


class ToolPolicyTests(unittest.TestCase):
    def test_mecanico_cannot_list_clients(self) -> None:
        self.assertFalse(
            is_tool_allowed(
                "listar_clientes",
                es_cliente=False,
                es_mecanico=True,
                es_propietario=False,
            )
        )

    def test_propietario_can_list_clients(self) -> None:
        self.assertTrue(
            is_tool_allowed(
                "listar_clientes",
                es_cliente=False,
                es_mecanico=False,
                es_propietario=True,
            )
        )

    def test_tools_for_session_hides_denied(self) -> None:
        mecanico_tools = tools_for_session(
            es_cliente=False,
            es_mecanico=True,
            es_propietario=False,
        )
        names = {t["function"]["name"] for t in mecanico_tools}
        self.assertNotIn("listar_clientes", names)
        self.assertLess(len(mecanico_tools), len(TOOL_DEFINITIONS))

    def test_redact_bulk_client_emails(self) -> None:
        rows = [{"id": 1, "nombre": "Ana", "email": "a@x.com", "telefono": "123"}]
        out = redact_tool_result("listar_clientes", rows)
        self.assertEqual(out[0]["email"], "[oculto]")
        self.assertEqual(out[0]["telefono"], "[oculto]")


if __name__ == "__main__":
    unittest.main()
