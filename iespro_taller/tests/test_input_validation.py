"""Tests de validación de entrada en catálogos."""

from __future__ import annotations

import unittest

from fastapi import HTTPException

from api.input_validation import (
  validate_branch_name,
  validate_catalog_description,
  validate_catalog_name,
  validate_catalog_price,
  validate_client_name,
  validate_free_text,
  validate_inventory_quantity,
)


class TestInputValidation(unittest.TestCase):
  def test_acepta_nombre_normal(self) -> None:
    self.assertEqual(validate_catalog_name("Filtro de aceite"), "Filtro de aceite")

  def test_rechaza_xss(self) -> None:
    with self.assertRaises(HTTPException):
      validate_catalog_name('<script>alert(1)</script>')

  def test_rechaza_ssti(self) -> None:
    with self.assertRaises(HTTPException):
      validate_catalog_name("{{7*7}}")
    with self.assertRaises(HTTPException):
      validate_catalog_description("${7*7}")

  def test_rechaza_sqli_almacenado(self) -> None:
    with self.assertRaises(HTTPException):
      validate_catalog_name('Producto"; DROP TABLE inventario;--')

  def test_rechaza_precio_absurdo(self) -> None:
    with self.assertRaises(HTTPException):
      validate_catalog_price(999_999)

  def test_rechaza_cantidad_absurda(self) -> None:
    with self.assertRaises(HTTPException):
      validate_inventory_quantity(99_999, field_label="La cantidad")

  def test_cliente_nombre_seguro(self) -> None:
    self.assertEqual(validate_client_name("Juan Pérez"), "Juan Pérez")

  def test_texto_libre_rechaza_xss(self) -> None:
    with self.assertRaises(HTTPException):
      validate_free_text("<img src=x onerror=alert(1)>", field_label="Nota")

  def test_sucursal_nombre_seguro(self) -> None:
    self.assertEqual(validate_branch_name("Taller Centro"), "Taller Centro")


if __name__ == "__main__":
  unittest.main()
