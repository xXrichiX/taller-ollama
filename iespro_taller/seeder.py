#!/usr/bin/env python3
"""Sembrado masivo de datos para pruebas de escala (Semana 7).

Uso:
  cd iespro_taller && python seeder.py --count 10000
  python seeder.py --count 50000 --sync-rag
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from db.connection import db_cursor, execute, fetch_all, fetch_one  # noqa: E402
from db.init_db import init_database  # noqa: E402
from services import catalog_service  # noqa: E402

FALLAS = [
  "Ruido al frenar en llanta delantera derecha",
  "Vibración al acelerar sobre 80 km/h",
  "Fuga de aceite en cárter",
  "Check engine encendido intermitente",
  "Aire acondicionado no enfría",
  "Dificultad para arrancar en frío",
  "Humo azul al acelerar",
  "Dirección dura en baja velocidad",
  "Parabrisas con rajadura pequeña",
  "Luces intermitentes fallan",
]

ESTADOS = ["PENDIENTE", "EN_PROCESO", "COMPLETADA", "CANCELADA", "DIAGNOSTICO"]


def ensure_demo_sucursal() -> tuple[int, int, list[int], list[int]]:
  row = fetch_one("SELECT id FROM sucursales WHERE activo = 1 ORDER BY id LIMIT 1")
  if row:
    id_sucursal = row["id"]
  else:
    id_sucursal = catalog_service.create_sucursal("Sucursal Demo Escala", "Av. Prueba 100")

  mt = fetch_one("SELECT id FROM mi_taller WHERE id_sucursal = %s", (id_sucursal,))
  if not mt:
    id_mi_taller = execute(
      "INSERT INTO mi_taller (nombre, id_sucursal) VALUES (%s, %s)",
      ("Taller Demo", id_sucursal),
    )
  else:
    id_mi_taller = mt["id"]

  isla_count = fetch_one(
    "SELECT COUNT(*) AS n FROM islas i JOIN mi_taller m ON m.id = i.id_mi_taller WHERE m.id_sucursal = %s",
    (id_sucursal,),
  )
  if not isla_count or isla_count["n"] < 3:
    for n in range(1, 4):
      execute(
        "INSERT INTO islas (nombre, id_mi_taller, activo) VALUES (%s, %s, 1)",
        (f"Isla {n}", id_mi_taller),
      )

  isla_ids = [r["id"] for r in fetch_all(
    "SELECT i.id FROM islas i JOIN mi_taller m ON m.id = i.id_mi_taller WHERE m.id_sucursal = %s",
    (id_sucursal,),
  )]

  mec = fetch_all(
    """
    SELECT u.id FROM usuarios u
    JOIN roles r ON r.id = u.id_rol
    WHERE r.nombre = 'MECANICO' AND u.activo = 1 LIMIT 5
    """
  )
  if not mec:
    mec_id = execute(
      """
      INSERT INTO usuarios (nombre, email, password, id_rol, id_sucursal, es_trabajador, id_puesto, activo)
      VALUES (%s, %s, %s, 2, %s, 1, 2, 1)
      """,
      ("Mecánico Demo", "mecanico.demo@iespro.mx", "demo1234", id_sucursal),
    )
    catalog_service.set_usuario_sucursales(mec_id, [id_sucursal])
    mec_ids = [mec_id]
  else:
    mec_ids = [m["id"] for m in mec]

  existing = catalog_service.list_tipos_mantenimiento(id_sucursal)
  if not existing:
    catalog_service.create_tipo_mantenimiento(
      "Diagnóstico general", "Escaneo y revisión", 500.0, id_sucursal
    )
  return id_sucursal, id_mi_taller, isla_ids, mec_ids


def seed_bulk(count: int) -> dict:
  id_sucursal, _mt, isla_ids, mec_ids = ensure_demo_sucursal()
  admin = fetch_one("SELECT id FROM usuarios WHERE email = 'admin@iespro.mx'")
  id_admin = admin["id"] if admin else 1

  start = time.perf_counter()
  batch = 500
  clientes_creados = 0
  vehiculos_creados = 0
  citas_creadas = 0
  fallas_creadas = 0

  base_date = datetime.now() - timedelta(days=365)

  for offset in range(0, count, batch):
    size = min(batch, count - offset)
    cliente_rows = []
    for i in range(size):
      idx = offset + i
      cliente_rows.append((f"Cliente Demo {idx:06d}", f"cliente{idx:06d}@demo.mx", id_admin))

    with db_cursor() as cur:
      cur.executemany(
        "INSERT INTO clientes (nombre, email, id_usuario) VALUES (%s, %s, %s)",
        cliente_rows,
      )

      emails = [f"cliente{offset + i:06d}@demo.mx" for i in range(size)]
      placeholders = ",".join(["%s"] * size)
      cur.execute(
        f"SELECT id FROM clientes WHERE email IN ({placeholders}) ORDER BY id",
        emails,
      )
      cliente_ids = [r["id"] for r in cur.fetchall()]

      vehiculo_rows = []
      for i, id_cliente in enumerate(cliente_ids):
        idx = offset + i
        placa = f"D{idx:05d}"
        vehiculo_rows.append((
          f"ECO-{idx:05d}",
          placa,
          f"SER{idx:08d}",
          random.randint(1, 4),
          f"Modelo {idx % 50}",
          random.randint(1, 4),
          random.randint(1, 4),
          random.randint(10000, 200000),
          id_cliente,
          id_admin,
          id_sucursal,
          random.choice(mec_ids),
        ))

      cur.executemany(
        """
        INSERT INTO vehiculos (
          numero_economico, placa, serie, id_marca, modelo,
          id_tipo_combustible, id_tipo_unidad, kilometraje,
          id_cliente, id_usuario, id_sucursal, id_mecanico_asignado
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        vehiculo_rows,
      )

      placas = [f"D{offset + i:05d}" for i in range(size)]
      ph2 = ",".join(["%s"] * size)
      cur.execute(
        f"SELECT id, placa FROM vehiculos WHERE placa IN ({ph2}) ORDER BY id",
        placas,
      )
      vehiculo_map = {r["placa"]: r["id"] for r in cur.fetchall()}

      cita_rows = []
      for i in range(size):
        idx = offset + i
        placa = f"D{idx:05d}"
        id_cliente = cliente_ids[i]
        id_vehiculo = vehiculo_map[placa]
        fecha = base_date + timedelta(days=idx % 300, hours=idx % 8 + 8)
        compromiso = (fecha + timedelta(days=2)).date()
        cita_rows.append((
          id_cliente,
          id_vehiculo,
          id_sucursal,
          fecha,
          random.choice(mec_ids),
          random.choice(isla_ids),
          random.choice(FALLAS),
          compromiso,
          fecha.time(),
          random.choice(ESTADOS),
        ))

      cur.executemany(
        """
        INSERT INTO citas (
          id_cliente, id_vehiculo, id_sucursal, fecha_cita,
          id_mecanico, id_isla, descripcion_fallo,
          fecha_compromiso, hora_compromiso, estado
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        cita_rows,
      )

      cur.execute(
        f"""
        SELECT c.id, c.id_vehiculo FROM citas c
        JOIN vehiculos v ON v.id = c.id_vehiculo
        WHERE v.placa IN ({ph2})
        ORDER BY c.id
        """,
        placas,
      )
      cita_pairs = cur.fetchall()

      falla_rows = []
      for i, row in enumerate(cita_pairs):
        idx = offset + i
        falla_rows.append((
          row["id"],
          row["id_vehiculo"],
          random.choice(FALLAS) + f" (caso {idx})",
          f"Diagnóstico preliminar {idx % 20}",
          f"Observación técnica {idx}",
          "Revisión pendiente" if idx % 3 else "Servicio completado",
          1 if idx % 4 == 0 else 0,
        ))

      cur.executemany(
        """
        INSERT INTO fallas_registradas (
          id_cita, id_vehiculo, descripcion, diagnostico, observaciones, solucion, resuelto
        ) VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        falla_rows,
      )

    clientes_creados += size
    vehiculos_creados += size
    citas_creadas += size
    fallas_creadas += size
    print(f"  ... {citas_creadas}/{count} citas")

  elapsed = time.perf_counter() - start
  total_citas = fetch_one("SELECT COUNT(*) AS n FROM citas")["n"]
  return {
    "id_sucursal": id_sucursal,
    "clientes": clientes_creados,
    "vehiculos": vehiculos_creados,
    "citas_insertadas": citas_creadas,
    "fallas_insertadas": fallas_creadas,
    "total_citas_bd": total_citas,
    "segundos": round(elapsed, 2),
  }


def main():
  parser = argparse.ArgumentParser(description="Seeder masivo IESPRO-Taller")
  parser.add_argument("--count", type=int, default=10000, help="Número de citas a insertar")
  parser.add_argument("--sync-rag", action="store_true", help="Sincronizar Chroma tras sembrar")
  args = parser.parse_args()

  print("Inicializando base de datos...")
  init_database()

  print(f"Sembrando {args.count} registros (bulk/transacciones)...")
  stats = seed_bulk(args.count)
  print("\n=== Resumen ===")
  for k, v in stats.items():
    print(f"  {k}: {v}")

  if args.sync_rag:
    print("\nSincronizando RAG...")
    from services.rag_service import RagService
    rag = RagService()
    added = rag.sync_fallas_from_db()
    print(f"  Fallas indexadas nuevas: {added}")
    print(f"  Total vectorial: {rag.info()}")


if __name__ == "__main__":
  main()
