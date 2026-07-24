from pathlib import Path

from db.connection import execute, execute_script_file, fetch_one, get_connection, test_connection
from config import BASE_DIR, MYSQL_DATABASE

_META_KEY = "minimal_seed_v2"

_BUSINESS_TABLES = (
    "mensajes_chat",
    "conversaciones",
    "llm_observability_logs",
    "cita_servicios",
    "fallas_registradas",
    "citas",
    "isla_mecanicos",
    "islas",
    "mi_taller",
    "horarios",
    "vehiculos",
    "clientes",
    "usuario_sucursales",
    "tipos_mantenimiento",
    "sucursales",
)


def init_database() -> tuple[bool, str]:
    schema = BASE_DIR / "sql" / "schema.sql"

    try:
        execute_script_file(str(schema), database=None)
        ensure_minimal_data_only()
        ensure_bootstrap_sucursal()
        ensure_performance_indexes()
        ok, msg = test_connection()
        return ok, msg if ok else msg
    except Exception as exc:
        return False, f"Error inicializando BD: {exc}"


_INDEXES = (
    ("citas", "idx_citas_sucursal", "id_sucursal"),
    ("citas", "idx_citas_mecanico", "id_mecanico"),
    ("citas", "idx_citas_estado", "estado"),
    ("citas", "idx_citas_fecha", "fecha_cita"),
    ("vehiculos", "idx_vehiculos_placa", "placa"),
    ("vehiculos", "idx_vehiculos_sucursal", "id_sucursal"),
    ("fallas_registradas", "idx_fallas_vehiculo", "id_vehiculo"),
    ("fallas_registradas", "idx_fallas_cita", "id_cita"),
)


def ensure_performance_indexes() -> None:
    """Crea índices B-Tree idempotentes para consultas a escala (Semana 7)."""
    for table, index_name, column in _INDEXES:
        exists = fetch_one(
            """
            SELECT COUNT(*) AS n FROM information_schema.statistics
            WHERE table_schema = %s AND table_name = %s AND index_name = %s
            """,
            (MYSQL_DATABASE, table, index_name),
        )
        if exists and exists["n"]:
            continue
        execute(f"CREATE INDEX {index_name} ON {table}({column})")


def ensure_minimal_data_only() -> None:
    """Elimina datos de negocio viejos (semillas demo). Solo queda admin + catálogos."""
    row = fetch_one(
        "SELECT meta_value FROM app_meta WHERE meta_key = %s",
        (_META_KEY,),
    )
    if row:
        return

    _purge_business_data()
    execute(
        "INSERT INTO app_meta (meta_key, meta_value) VALUES (%s, %s)",
        (_META_KEY, "1"),
    )


def ensure_bootstrap_sucursal() -> None:
    """Garantiza al menos una sucursal para que admin pueda usar la API web."""
    row = fetch_one("SELECT id FROM sucursales WHERE activo = 1 LIMIT 1")
    if row:
        return
    from services import catalog_service

    catalog_service.create_sucursal("Sucursal Principal", "Instalación inicial")


def _purge_business_data() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in _BUSINESS_TABLES:
                cur.execute(
                    """
                    SELECT COUNT(*) AS n FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                    """,
                    (MYSQL_DATABASE, table),
                )
                if cur.fetchone()["n"]:
                    cur.execute(f"TRUNCATE TABLE `{table}`")
            cur.execute(
                "DELETE FROM usuarios WHERE LOWER(email) <> %s",
                ("admin@iespro.mx",),
            )
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_data_dir() -> None:
    from config import CHROMA_PATH, DOCUMENTS_PATH
    from pathlib import Path

    Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
    DOCUMENTS_PATH.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
