from pathlib import Path

from db.connection import execute, execute_script_file, fetch_all, fetch_one, get_connection, test_connection
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
    "inventario",
    "sucursales",
)


def init_database() -> tuple[bool, str]:
    schema = BASE_DIR / "sql" / "schema.sql"

    try:
        if not _database_bootstrapped():
            try:
                execute_script_file(str(schema), database=None)
            except Exception as exc:
                msg = str(exc).lower()
                if "access denied" in msg or "privilege" in msg:
                    return (
                        False,
                        "BD sin inicializar: arranca MySQL con schema.sql (Docker) "
                        "o ejecuta el esquema con usuario root.",
                    )
                raise
        ensure_catalog_seeds()
        ensure_minimal_data_only()
        ensure_schema_migrations()
        ensure_inventario_table()
        ensure_inventario_isla_column()
        ensure_clientes_sucursal_column()
        ensure_remove_legacy_admin()
        ensure_roles_simplified()
        ensure_deactivate_compromised_sucursales()
        ensure_performance_indexes()
        ok, msg = test_connection()
        return ok, msg if ok else msg
    except Exception as exc:
        return False, f"Error inicializando BD: {exc}"


def _database_bootstrapped() -> bool:
    row = fetch_one(
        """
        SELECT COUNT(*) AS n FROM information_schema.tables
        WHERE table_schema = %s AND table_name = 'usuarios'
        """,
        (MYSQL_DATABASE,),
    )
    return bool(row and row["n"])


_INDEXES = (
    ("citas", "idx_citas_sucursal", "id_sucursal"),
    ("citas", "idx_citas_mecanico", "id_mecanico"),
    ("citas", "idx_citas_isla", "id_isla"),
    ("inventario", "idx_inventario_isla", "id_isla"),
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


def ensure_schema_migrations() -> None:
    """Columnas añadidas después del esquema inicial."""
    col = fetch_one(
        """
        SELECT COUNT(*) AS n FROM information_schema.columns
        WHERE table_schema = %s AND table_name = 'sucursales' AND column_name = 'id_propietario'
        """,
        (MYSQL_DATABASE,),
    )
    if col and col["n"]:
        return
    execute(
        """
        ALTER TABLE sucursales
        ADD COLUMN id_propietario INT NULL
        """
    )
    execute(
        """
        UPDATE sucursales s
        JOIN usuarios u ON u.id_sucursal = s.id
        SET s.id_propietario = u.id
        WHERE s.id_propietario IS NULL
        """
    )


def ensure_inventario_table() -> None:
    exists = fetch_one(
        """
        SELECT COUNT(*) AS n FROM information_schema.tables
        WHERE table_schema = %s AND table_name = 'inventario'
        """,
        (MYSQL_DATABASE,),
    )
    if exists and exists["n"]:
        return
    execute(
        """
        CREATE TABLE inventario (
          id INT AUTO_INCREMENT PRIMARY KEY,
          codigo VARCHAR(40),
          nombre VARCHAR(120) NOT NULL,
          descripcion TEXT,
          cantidad DECIMAL(10, 2) NOT NULL DEFAULT 0,
          stock_minimo DECIMAL(10, 2) NOT NULL DEFAULT 0,
          precio_unitario DECIMAL(10, 2) NOT NULL DEFAULT 0,
          unidad VARCHAR(20) NOT NULL DEFAULT 'pza',
          id_sucursal INT NOT NULL,
          id_isla INT NOT NULL,
          activo TINYINT(1) NOT NULL DEFAULT 1,
          FOREIGN KEY (id_sucursal) REFERENCES sucursales(id),
          FOREIGN KEY (id_isla) REFERENCES islas(id)
        )
        """
    )


def ensure_inventario_isla_column() -> None:
    col = fetch_one(
        """
        SELECT COUNT(*) AS n FROM information_schema.columns
        WHERE table_schema = %s AND table_name = 'inventario' AND column_name = 'id_isla'
        """,
        (MYSQL_DATABASE,),
    )
    if col and col["n"]:
        return
    execute("ALTER TABLE inventario ADD COLUMN id_isla INT NULL AFTER id_sucursal")
    rows = fetch_all("SELECT DISTINCT id_sucursal FROM inventario WHERE id_isla IS NULL")
    for row in rows:
        sid = row["id_sucursal"]
        isla = fetch_one(
            """
            SELECT i.id FROM islas i
            JOIN mi_taller m ON m.id = i.id_mi_taller
            WHERE m.id_sucursal = %s
            ORDER BY i.id
            LIMIT 1
            """,
            (sid,),
        )
        if isla:
            execute(
                "UPDATE inventario SET id_isla = %s WHERE id_sucursal = %s AND id_isla IS NULL",
                (isla["id"], sid),
            )
    execute("ALTER TABLE inventario MODIFY COLUMN id_isla INT NOT NULL")
    fk = fetch_one(
        """
        SELECT COUNT(*) AS n FROM information_schema.table_constraints
        WHERE table_schema = %s AND table_name = 'inventario'
          AND constraint_name = 'inventario_ibfk_isla'
        """,
        (MYSQL_DATABASE,),
    )
    if not fk or not fk["n"]:
        execute(
            """
            ALTER TABLE inventario
            ADD CONSTRAINT inventario_ibfk_isla FOREIGN KEY (id_isla) REFERENCES islas(id)
            """
        )


def _ensure_role(nombre: str, descripcion: str) -> None:
    """Inserta o actualiza un rol por nombre (evita choque UNIQUE en BD migrada)."""
    row = fetch_one("SELECT id FROM roles WHERE nombre = %s", (nombre,))
    if row:
        execute(
            "UPDATE roles SET descripcion = %s WHERE id = %s",
            (descripcion, int(row["id"])),
        )
        return
    execute(
        "INSERT INTO roles (nombre, descripcion) VALUES (%s, %s)",
        (nombre, descripcion),
    )


def _ensure_puesto(nombre: str) -> None:
    if fetch_one("SELECT id FROM puestos WHERE nombre = %s", (nombre,)):
        return
    execute("INSERT INTO puestos (nombre) VALUES (%s)", (nombre,))


def ensure_catalog_seeds() -> None:
    """Catálogos mínimos (roles, puestos, marcas). Idempotente en cada arranque."""
    _ensure_role("MECANICO", "Dueño o mecánico del taller")
    _ensure_role("CLIENTE", "Cliente con acceso a la app")
    _ensure_puesto("Mecánico")
    execute(
        """
        INSERT IGNORE INTO marcas (id, nombre) VALUES
        (1, 'Nissan'), (2, 'Toyota'), (3, 'Ford'), (4, 'Chevrolet')
        """
    )
    execute(
        """
        INSERT IGNORE INTO tipos_combustible (id, nombre) VALUES
        (1, 'Gasolina'), (2, 'Diésel'), (3, 'Híbrido'), (4, 'Eléctrico')
        """
    )
    execute(
        """
        INSERT IGNORE INTO tipos_unidad (id, nombre) VALUES
        (1, 'Sedán'), (2, 'Pickup'), (3, 'SUV'), (4, 'Camioneta')
        """
    )


def ensure_clientes_sucursal_column() -> None:
    col = fetch_one(
        """
        SELECT COUNT(*) AS n FROM information_schema.columns
        WHERE table_schema = %s AND table_name = 'clientes' AND column_name = 'id_sucursal'
        """,
        (MYSQL_DATABASE,),
    )
    if col and col["n"]:
        return
    execute("ALTER TABLE clientes ADD COLUMN id_sucursal INT NULL AFTER id_usuario")
    execute(
        """
        UPDATE clientes c
        JOIN (
          SELECT id_cliente, MIN(id_sucursal) AS id_sucursal
          FROM vehiculos
          GROUP BY id_cliente
        ) v ON v.id_cliente = c.id
        SET c.id_sucursal = v.id_sucursal
        WHERE c.id_sucursal IS NULL
        """
    )
    fk = fetch_one(
        """
        SELECT COUNT(*) AS n FROM information_schema.table_constraints
        WHERE table_schema = %s AND table_name = 'clientes'
          AND constraint_name = 'clientes_ibfk_sucursal'
        """,
        (MYSQL_DATABASE,),
    )
    if not fk or not fk["n"]:
        execute(
            """
            ALTER TABLE clientes
            ADD CONSTRAINT clientes_ibfk_sucursal
            FOREIGN KEY (id_sucursal) REFERENCES sucursales(id)
            """
        )


def ensure_remove_legacy_admin() -> None:
    """Elimina la cuenta global de administrador (modelo multi-taller por registro)."""
    execute("DELETE FROM usuarios WHERE LOWER(email) = %s", ("admin@iespro.mx",))


def ensure_deactivate_compromised_sucursales() -> None:
    """Desactiva sucursales con nombres de compromiso conocidos (p. ej. HACKED_SUCURSAL)."""
    import logging
    import re

    from services import audit_actions as audit_actions
    from services.audit_service import audit as log_audit

    logger = logging.getLogger(__name__)
    suspicious_re = re.compile(r"(hacked|backdoor|pwned|malicious|injected)", re.I)
    rows = fetch_all(
        "SELECT id, nombre FROM sucursales WHERE activo = 1",
    )
    for row in rows:
        nombre = str(row.get("nombre") or "")
        if not suspicious_re.search(nombre):
            continue
        sid = int(row["id"])
        logger.warning("Desactivando sucursal comprometida id=%s nombre=%s", sid, nombre)
        execute("UPDATE sucursales SET activo = 0 WHERE id = %s", (sid,))
        log_audit(
            accion=audit_actions.COMPROMISED_SUCURSAL,
            recurso=f"sucursal:{sid}",
            detalle=nombre[:120],
            resultado="deactivated",
        )


def ensure_roles_simplified() -> None:
    """Migra roles legacy (ADMIN, PENDIENTE…) a MECANICO y deja solo Mecánico + Cliente."""
    mec = fetch_one("SELECT id FROM roles WHERE nombre = 'MECANICO' LIMIT 1")
    if not mec:
        return
    mec_id = int(mec["id"])

    for legacy in ("ADMIN", "SUPER_ADMIN", "PENDIENTE"):
        row = fetch_one("SELECT id FROM roles WHERE nombre = %s", (legacy,))
        if not row:
            continue
        legacy_id = int(row["id"])
        execute("UPDATE usuarios SET id_rol = %s WHERE id_rol = %s", (mec_id, legacy_id))
        execute("DELETE FROM roles WHERE id = %s", (legacy_id,))

    mecanico_roles = fetch_all("SELECT id FROM roles WHERE nombre = 'MECANICO' ORDER BY id")
    if len(mecanico_roles) > 1:
        keep_id = int(mecanico_roles[0]["id"])
        for extra in mecanico_roles[1:]:
            extra_id = int(extra["id"])
            execute("UPDATE usuarios SET id_rol = %s WHERE id_rol = %s", (keep_id, extra_id))
            execute("DELETE FROM roles WHERE id = %s", (extra_id,))

    cliente_roles = fetch_all("SELECT id FROM roles WHERE nombre = 'CLIENTE' ORDER BY id")
    if len(cliente_roles) > 1:
        keep_id = int(cliente_roles[0]["id"])
        for extra in cliente_roles[1:]:
            extra_id = int(extra["id"])
            execute("UPDATE usuarios SET id_rol = %s WHERE id_rol = %s", (keep_id, extra_id))
            execute("DELETE FROM roles WHERE id = %s", (extra_id,))

    puesto_mec = fetch_one("SELECT id FROM puestos WHERE nombre = 'Mecánico' LIMIT 1")
    if puesto_mec:
        pm_id = int(puesto_mec["id"])
        admin_puesto = fetch_one("SELECT id FROM puestos WHERE nombre = 'Admin' LIMIT 1")
        if admin_puesto:
            execute(
                "UPDATE usuarios SET id_puesto = %s WHERE id_puesto = %s",
                (pm_id, int(admin_puesto["id"])),
            )
            execute("DELETE FROM puestos WHERE id = %s", (int(admin_puesto["id"]),))


def ensure_minimal_data_only() -> None:
    """Elimina datos de negocio viejos (semillas demo). Solo quedan catálogos base."""
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
            cur.execute("DELETE FROM usuarios")
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
