from typing import Any

from db.connection import execute, fetch_all, fetch_one


def list_inventario(id_isla: int) -> list[dict]:
    rows = fetch_all(
        """
        SELECT id, codigo, nombre, descripcion, cantidad, stock_minimo,
               precio_unitario, unidad, activo, id_isla
        FROM inventario
        WHERE id_isla = %s AND activo = 1
        ORDER BY nombre
        """,
        (id_isla,),
    )
    for row in rows:
        row["cantidad"] = float(row.get("cantidad") or 0)
        row["stock_minimo"] = float(row.get("stock_minimo") or 0)
        row["precio_unitario"] = float(row.get("precio_unitario") or 0)
        row["stock_bajo"] = row["cantidad"] <= row["stock_minimo"]
    return rows


def get_item(id_item: int, id_isla: int) -> dict | None:
    row = fetch_one(
        """
        SELECT id, codigo, nombre, descripcion, cantidad, stock_minimo,
               precio_unitario, unidad, activo, id_sucursal, id_isla
        FROM inventario
        WHERE id = %s AND id_isla = %s
        """,
        (id_item, id_isla),
    )
    if not row:
        return None
    row["cantidad"] = float(row.get("cantidad") or 0)
    row["stock_minimo"] = float(row.get("stock_minimo") or 0)
    row["precio_unitario"] = float(row.get("precio_unitario") or 0)
    row["stock_bajo"] = row["cantidad"] <= row["stock_minimo"]
    return row


def create_item(id_sucursal: int, id_isla: int, data: dict) -> int:
    return execute(
        """
        INSERT INTO inventario (
            codigo, nombre, descripcion, cantidad, stock_minimo,
            precio_unitario, unidad, id_sucursal, id_isla
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            (data.get("codigo") or "").strip() or None,
            data["nombre"].strip(),
            (data.get("descripcion") or "").strip() or None,
            data.get("cantidad", 0),
            data.get("stock_minimo", 0),
            data.get("precio_unitario", 0),
            (data.get("unidad") or "pza").strip() or "pza",
            id_sucursal,
            id_isla,
        ),
    )


def update_item(id_item: int, id_isla: int, data: dict) -> dict[str, Any]:
    item = get_item(id_item, id_isla)
    if not item:
        return {"ok": False, "error": "Artículo no encontrado."}
    execute(
        """
        UPDATE inventario
        SET codigo = %s, nombre = %s, descripcion = %s,
            cantidad = %s, stock_minimo = %s, precio_unitario = %s, unidad = %s
        WHERE id = %s AND id_isla = %s
        """,
        (
            (data.get("codigo") or "").strip() or None,
            data["nombre"].strip(),
            (data.get("descripcion") or "").strip() or None,
            data.get("cantidad", item["cantidad"]),
            data.get("stock_minimo", item["stock_minimo"]),
            data.get("precio_unitario", item["precio_unitario"]),
            (data.get("unidad") or item["unidad"]).strip() or "pza",
            id_item,
            id_isla,
        ),
    )
    return {"ok": True}


def ajustar_stock(id_item: int, id_isla: int, delta: float) -> dict[str, Any]:
    item = get_item(id_item, id_isla)
    if not item:
        return {"ok": False, "error": "Artículo no encontrado."}
    nueva = float(item["cantidad"]) + float(delta)
    if nueva < 0:
        return {"ok": False, "error": "No hay suficiente stock."}
    execute(
        "UPDATE inventario SET cantidad = %s WHERE id = %s AND id_isla = %s",
        (nueva, id_item, id_isla),
    )
    return {"ok": True, "cantidad": nueva}
