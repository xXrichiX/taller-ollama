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
        execute_script_file(str(schema), database=None)
        ensure_catalog_seeds()
        ensure_minimal_data_only()
        ensure_schema_migrations()
        ensure_inventario_table()
        ensure_inventario_isla_column()
        ensure_remove_legacy_admin()
        ensure_roles_simplified()
        ensure_performance_indexes()
        ok, msg = test_connection()
        return ok, msg if ok else msg
    except Exception as exc:
        return False, f"Error inicializando BD: {exc}"


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


def ensure_catalog_seeds() -> None:
    """Catálogos mínimos (roles, puestos, marcas). Idempotente en cada arranque."""
    execute(
        """
        INSERT INTO roles (id, nombre, descripcion) VALUES
        (1, 'MECANICO', 'Dueño o mecánico del taller'),
        (2, 'CLIENTE', 'Cliente con acceso a la app')
        ON DUPLICATE KEY UPDATE
          nombre = VALUES(nombre),
          descripcion = VALUES(descripcion)
        """
    )
    execute(
        """
        INSERT INTO puestos (id, nombre) VALUES
        (1, 'Mecánico')
        ON DUPLICATE KEY UPDATE nombre = VALUES(nombre)
        """
    )
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
    execute(
        """
        INSERT IGNORE INTO tipos_mantenimiento_plantilla (nombre, descripcion, precio) VALUES
        ('Cambio de aceite', 'Aceite y filtro', 850.00),
        ('Diagnóstico general', 'Escaneo y revisión', 500.00),
        ('Frenos delanteros', 'Balatas y discos', 2800.00),
        ('Alineación y balanceo', 'Alineación de dirección', 650.00),
        ('Servicio de transmisión', 'Cambio de aceite CVT/ATF', 1200.00),
        ('Revisión eléctrica', 'Batería, alternador, luces', 450.00)
        """
    )


def ensure_remove_legacy_admin() -> None:
    """Elimina la cuenta global de administrador (modelo multi-taller por registro)."""
    execute("DELETE FROM usuarios WHERE LOWER(email) = %s", ("admin@iespro.mx",))


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
