"""Tests de mensajes genéricos en producción (anti-enumeración)."""

from __future__ import annotations

import unittest
from unittest.mock import patch


class SecurityMessagesTests(unittest.TestCase):
  @patch("api.security_messages.IS_PRODUCTION", True)
  def test_forbidden_generic_in_prod(self) -> None:
    from api.security_messages import forbidden

    self.assertEqual(forbidden("Isla no permitida"), "Acceso denegado.")
    self.assertEqual(forbidden("Sucursal no permitida"), "Acceso denegado.")

  @patch("api.security_messages.IS_PRODUCTION", False)
  def test_forbidden_detailed_in_dev(self) -> None:
    from api.security_messages import forbidden

    self.assertEqual(forbidden("Isla no permitida"), "Isla no permitida")

  @patch("api.security_messages.IS_PRODUCTION", True)
  def test_captcha_failed_generic_in_prod(self) -> None:
    from api.security_messages import captcha_failed

    self.assertEqual(captcha_failed(), "No se pudo completar la verificación.")

  @patch("api.security_messages.IS_PRODUCTION", True)
  def test_setup_required_generic_in_prod(self) -> None:
    from api.security_messages import setup_required

    self.assertEqual(
      setup_required("Selecciona una isla activa"),
      "Completa la configuración requerida para continuar.",
    )


if __name__ == "__main__":
  unittest.main()
