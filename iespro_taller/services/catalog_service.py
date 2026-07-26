from typing import Any

from config import DEFAULT_SUCURSAL_ID
from db.connection import execute, fetch_all, fetch_one


def login(email: str, password: str) -> dict[str, Any] | None:
    user = fetch_one(
        """
        SELECT u.*, r.nombre AS rol_nombre, p.nombre AS puesto_nombre
        FROM usuarios u
        JOIN roles r ON r.id = u.id_rol
        LEFT JOIN puestos p ON p.id = u.id_puesto
        WHERE u.email = %s AND u.password = %s AND u.activo = 1
        """,
        (email, password),
    )
    if not user:
        return None
    return enrich_user_session(user)


def get_user_by_id(id_usuario: int) -> dict | None:
    user = fetch_one(
        """
        SELECT u.*, r.nombre AS rol_nombre, p.nombre AS puesto_nombre
        FROM usuarios u
        JOIN roles r ON r.id = u.id_rol
        LEFT JOIN puestos p ON p.id = u.id_puesto
        WHERE u.id = %s AND u.activo = 1
        """,
        (id_usuario,),
    )
    if not user:
        return None
    return enrich_user_session(user)


def list_sucursales_usuario(id_usuario: int) -> list[dict]:
    return fetch_all(
        """
        SELECT DISTINCT s.id, s.nombre, s.direccion, s.activo
        FROM sucursales s
        LEFT JOIN usuario_sucursales us
          ON us.id_sucursal = s.id AND us.id_usuario = %s
        WHERE s.activo = 1
          AND (s.id_propietario = %s OR us.id_usuario IS NOT NULL)
        ORDER BY s.nombre
        """,
        (id_usuario, id_usuario),
    )


def user_owns_sucursal(id_usuario: int, id_sucursal: int) -> bool:
    row = fetch_one(
        """
        SELECT id FROM sucursales
        WHERE id = %s AND activo = 1 AND id_propietario = %s
        """,
        (id_sucursal, id_usuario),
    )
    return bool(row)


def user_is_propietario(id_usuario: int) -> bool:
    row = fetch_one(
        "SELECT id FROM sucursales WHERE id_propietario = %s AND activo = 1 LIMIT 1",
        (id_usuario,),
    )
    return bool(row)


def user_can_create_sucursal(id_usuario: int) -> bool:
    branches = list_sucursales_usuario(id_usuario)
    if not branches:
        return True
    return user_is_propietario(id_usuario)


def user_needs_taller_setup(id_usuario: int, rol_nombre: str | None) -> bool:
    from services.user_roles import is_cliente, is_workshop_staff

    if is_cliente(rol_nombre) or not is_workshop_staff(rol_nombre):
        return False
    return not list_sucursales_usuario(id_usuario)


def user_can_access_sucursal(id_usuario: int, id_sucursal: int) -> bool:
    row = fetch_one(
        """
        SELECT s.id
        FROM sucursales s
        LEFT JOIN usuario_sucursales us
          ON us.id_sucursal = s.id AND us.id_usuario = %s
        WHERE s.id = %s AND s.activo = 1
          AND (s.id_propietario = %s OR us.id_usuario IS NOT NULL)
        """,
        (id_usuario, id_sucursal, id_usuario),
    )
    return bool(row)


def add_usuario_sucursal(id_usuario: int, id_sucursal: int) -> None:
    execute(
        "INSERT IGNORE INTO usuario_sucursales (id_usuario, id_sucursal) VALUES (%s, %s)",
        (id_usuario, id_sucursal),
    )


def set_usuario_sucursales(id_usuario: int, id_sucursales: list[int]) -> None:
    execute("DELETE FROM usuario_sucursales WHERE id_usuario = %s", (id_usuario,))
    for id_sucursal in id_sucursales:
        execute(
            "INSERT IGNORE INTO usuario_sucursales (id_usuario, id_sucursal) VALUES (%s, %s)",
            (id_usuario, id_sucursal),
        )


def enrich_user_session(user: dict) -> dict:
    from services.user_roles import is_cliente, is_workshop_staff

    if is_workshop_staff(user.get("rol_nombre")):
        user["sucursales_ids"] = [s["id"] for s in list_sucursales_usuario(user["id"])]
    elif is_cliente(user.get("rol_nombre")):
        sid = user.get("id_sucursal")
        user["sucursales_ids"] = [sid] if sid else []
    else:
        sid = user.get("id_sucursal")
        user["sucursales_ids"] = [sid] if sid else []
    user["es_propietario"] = user_is_propietario(user["id"])
    return user


def list_sucursales() -> list[dict]:
    return fetch_all("SELECT id, nombre, direccion, activo FROM sucursales WHERE activo = 1 ORDER BY nombre")


def list_roles() -> list[dict]:
    return fetch_all("SELECT id, nombre FROM roles ORDER BY id")


def list_puestos() -> list[dict]:
    return fetch_all(
        "SELECT id, nombre FROM puestos WHERE nombre IN ('Admin', 'Mecánico') ORDER BY nombre"
    )


def rol_from_puesto(puesto_nombre: str) -> tuple[int, str]:
    """Deriva rol interno desde puesto visible en UI (Admin → ADMIN, Mecánico → MECANICO)."""
    p = (puesto_nombre or "").strip().lower()
    if p == "admin":
        row = fetch_one("SELECT id, nombre FROM roles WHERE nombre = 'ADMIN'")
    else:
        row = fetch_one("SELECT id, nombre FROM roles WHERE nombre = 'MECANICO'")
    if not row:
        raise ValueError("Puesto no válido.")
    return int(row["id"]), row["nombre"]


def assign_usuario_staff(
    id_usuario: int,
    id_puesto: int,
    puesto_nombre: str,
    id_sucursales: list[int] | None = None,
) -> dict[str, Any]:
    """Asigna puesto y rol. Mecánico: una o varias sucursales. Admin: todas."""
    id_rol, rol_nombre = rol_from_puesto(puesto_nombre)
    update_usuario_puesto(id_usuario, id_puesto)
    result = update_usuario_rol(id_usuario, id_rol, rol_nombre)
    if rol_nombre == "ADMIN":
        execute("UPDATE usuarios SET id_sucursal = NULL WHERE id = %s", (id_usuario,))
        set_usuario_sucursales(id_usuario, [])
    elif id_sucursales:
        set_usuario_sucursales(id_usuario, id_sucursales)
        execute(
            "UPDATE usuarios SET id_sucursal = %s WHERE id = %s",
            (id_sucursales[0], id_usuario),
        )
    return result


def list_usuarios(id_sucursal: int | None = None) -> list[dict]:
    query = """
        SELECT u.id, u.nombre, u.email, r.nombre AS rol, p.nombre AS puesto,
               u.activo, u.id_sucursal, u.id_rol
        FROM usuarios u
        JOIN roles r ON r.id = u.id_rol
        LEFT JOIN puestos p ON p.id = u.id_puesto
        WHERE r.nombre IN ('ADMIN', 'MECANICO', 'PENDIENTE')
    """
    params: list[Any] = []
    if id_sucursal:
        query += """
          AND (
            u.id_rol = (SELECT id FROM roles WHERE nombre = 'ADMIN' LIMIT 1)
            OR u.id IN (SELECT id_usuario FROM usuario_sucursales WHERE id_sucursal = %s)
            OR u.id_sucursal = %s
          )
        """
        params.extend([id_sucursal, id_sucursal])
    query += " ORDER BY u.id"
    rows = fetch_all(query, tuple(params))
    for row in rows:
        sucursales = list_sucursales_usuario(row["id"])
        if sucursales:
            row["sucursal"] = ", ".join(s["nombre"] for s in sucursales)
        elif row.get("rol") == "ADMIN":
            row["sucursal"] = "Todas"
        else:
            row["sucursal"] = "—"
    return rows


def update_usuario_rol(id_usuario: int, id_rol: int, rol_nombre: str | None = None) -> dict[str, Any]:
    from services.user_roles import flags_for_role

    if not rol_nombre:
        row = fetch_one("SELECT nombre FROM roles WHERE id = %s", (id_rol,))
        rol_nombre = row["nombre"] if row else ""
    es_cliente, es_trabajador = flags_for_role(rol_nombre)
    execute(
        """
        UPDATE usuarios
        SET id_rol = %s, es_cliente = %s, es_trabajador = %s
        WHERE id = %s
        """,
        (id_rol, es_cliente, es_trabajador, id_usuario),
    )
    return {"ok": True}


def update_usuario_puesto(id_usuario: int, id_puesto: int | None) -> dict[str, Any]:
    execute("UPDATE usuarios SET id_puesto = %s WHERE id = %s", (id_puesto, id_usuario))
    return {"ok": True}


def update_usuario_perfil(
    id_usuario: int,
    nombre: str,
    email: str,
    password: str | None = None,
) -> dict[str, Any]:
    from services.password_policy import normalize_password, validate_password

    nombre = (nombre or "").strip()
    email = (email or "").strip().lower()
    if not nombre or not email:
        return {"ok": False, "error": "Nombre y correo son obligatorios."}
    if "@" not in email or "." not in email.split("@")[-1]:
        return {"ok": False, "error": "Indica un correo válido."}

    existing = fetch_one(
        "SELECT id FROM usuarios WHERE LOWER(email) = %s AND id != %s",
        (email, id_usuario),
    )
    if existing:
        return {"ok": False, "error": "Ese correo ya está en uso."}

    if password:
        password = normalize_password(password)
        ok, msg = validate_password(password, email)
        if not ok:
            return {"ok": False, "error": msg}
        execute(
            "UPDATE usuarios SET nombre = %s, email = %s, password = %s WHERE id = %s",
            (nombre, email, password, id_usuario),
        )
    else:
        execute(
            "UPDATE usuarios SET nombre = %s, email = %s WHERE id = %s",
            (nombre, email, id_usuario),
        )
    return {"ok": True}


def create_sucursal(nombre: str, direccion: str = "", id_propietario: int | None = None) -> int:
    id_sucursal = execute(
        "INSERT INTO sucursales (nombre, direccion, id_propietario) VALUES (%s, %s, %s)",
        (nombre.strip(), direccion.strip(), id_propietario),
    )
    copiar_tipos_mantenimiento_plantilla(id_sucursal)
    return id_sucursal


def update_sucursal(id_sucursal: int, nombre: str, direccion: str, activo: bool = True) -> dict[str, Any]:
    execute(
        "UPDATE sucursales SET nombre = %s, direccion = %s, activo = %s WHERE id = %s",
        (nombre.strip(), direccion.strip(), int(activo), id_sucursal),
    )
    return {"ok": True}


def get_sucursal(id_sucursal: int) -> dict | None:
    return fetch_one("SELECT id, nombre, direccion, activo FROM sucursales WHERE id = %s", (id_sucursal,))


def provision_taller_personal(id_usuario: int, nombre_usuario: str) -> int | None:
    """Crea el taller (sucursal) del dueño/mecánico. Las islas las crea el usuario después."""
    branches = list_sucursales_usuario(id_usuario)
    if branches:
        return int(branches[0]["id"])

    nombre_taller = f"Taller de {(nombre_usuario or '').strip()}" or "Mi taller"
    id_sucursal = create_sucursal(nombre_taller, "", id_propietario=id_usuario)
    add_usuario_sucursal(id_usuario, id_sucursal)
    execute(
        "UPDATE usuarios SET id_sucursal = %s WHERE id = %s",
        (id_sucursal, id_usuario),
    )
    return id_sucursal


def register_usuario(
    nombre: str,
    email: str,
    password: str,
) -> dict[str, Any]:
    """Registra dueño/mecánico y provisiona su taller (sucursal) automáticamente."""
    from services.password_policy import normalize_password, validate_password

    nombre = (nombre or "").strip()
    email = (email or "").strip().lower()
    password = normalize_password(password)

    if not nombre or not email or not password:
        return {"ok": False, "error": "Nombre, correo y contraseña son obligatorios."}
    if "@" not in email or "." not in email.split("@")[-1]:
        return {"ok": False, "error": "Indica un correo válido."}

    ok, msg = validate_password(password, email)
    if not ok:
        return {"ok": False, "error": msg}

    if fetch_one("SELECT id FROM usuarios WHERE LOWER(email) = %s", (email,)):
        return {"ok": False, "error": "Ese correo ya está registrado."}

    rol = fetch_one("SELECT id FROM roles WHERE nombre = 'MECANICO'")
    puesto = fetch_one("SELECT id FROM puestos WHERE nombre = 'Mecánico'")
    if not rol or not puesto:
        return {"ok": False, "error": "No está configurado el puesto Mecánico."}

    id_usuario = create_usuario({
        "nombre": nombre,
        "email": email,
        "password": password,
        "id_rol": int(rol["id"]),
        "id_sucursal": None,
        "es_cliente": 0,
        "es_trabajador": 1,
        "id_puesto": int(puesto["id"]),
    })
    provision_taller_personal(id_usuario, nombre)
    return {
        "ok": True,
        "id_usuario": id_usuario,
    }


def create_usuario(data: dict) -> int:
    from services.user_roles import flags_for_role

    if data.get("puesto_nombre") and not data.get("id_rol"):
        id_rol, rol_nombre = rol_from_puesto(data["puesto_nombre"])
        data["id_rol"] = id_rol
    rol = fetch_one("SELECT nombre FROM roles WHERE id = %s", (data["id_rol"],))
    rol_nombre = rol["nombre"] if rol else ""
    es_cliente, es_trabajador = flags_for_role(rol_nombre)
    if "es_cliente" in data:
        es_cliente = data["es_cliente"]
    if "es_trabajador" in data:
        es_trabajador = data["es_trabajador"]
    return execute(
        """
        INSERT INTO usuarios (nombre, email, password, id_rol, id_sucursal, es_cliente, es_trabajador, id_puesto)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            data["nombre"], data["email"], data["password"], data["id_rol"],
            data.get("id_sucursal"), es_cliente, es_trabajador,
            data.get("id_puesto"),
        ),
    )


def list_clientes(id_sucursal: int | None = None, id_mecanico: int | None = None) -> list[dict]:
    if id_sucursal:
        return fetch_all(
            """
            SELECT c.id, c.nombre, c.telefono, c.email, c.id_usuario, u.email AS usuario_email
            FROM clientes c
            LEFT JOIN usuarios u ON u.id = c.id_usuario
            ORDER BY c.nombre
            """
        )
    if id_mecanico:
        return fetch_all(
            """
            SELECT DISTINCT c.id, c.nombre, c.telefono, c.email, c.id_usuario, u.email AS usuario_email
            FROM clientes c
            LEFT JOIN usuarios u ON u.id = c.id_usuario
            LEFT JOIN vehiculos v ON v.id_cliente = c.id AND v.id_mecanico_asignado = %s
            LEFT JOIN citas ct ON ct.id_cliente = c.id AND ct.id_mecanico = %s
            WHERE v.id IS NOT NULL OR ct.id IS NOT NULL
            ORDER BY c.nombre
            """,
            (id_mecanico, id_mecanico),
        )
    return fetch_all(
        """
        SELECT c.id, c.nombre, c.telefono, c.email, c.id_usuario, u.email AS usuario_email
        FROM clientes c
        LEFT JOIN usuarios u ON u.id = c.id_usuario
        ORDER BY c.nombre
        """
    )


def get_cliente_by_usuario(id_usuario: int) -> dict | None:
    return fetch_one(
        """
        SELECT c.id, c.nombre, c.telefono, c.email, c.id_usuario
        FROM clientes c
        WHERE c.id_usuario = %s
        """,
        (id_usuario,),
    )


def create_cliente(nombre: str, telefono: str, email: str, id_usuario: int | None) -> int:
    return execute(
        "INSERT INTO clientes (nombre, telefono, email, id_usuario) VALUES (%s, %s, %s, %s)",
        (nombre, telefono, email, id_usuario),
    )


def ensure_cliente_usuario(id_cliente: int) -> int:
    """Vincula un usuario CLIENTE si el cliente llegó al mostrador sin app."""
    cliente = fetch_one(
        "SELECT id, nombre, telefono, email, id_usuario FROM clientes WHERE id = %s",
        (id_cliente,),
    )
    if not cliente:
        raise ValueError("Cliente no encontrado.")
    if cliente.get("id_usuario"):
        return int(cliente["id_usuario"])

    email = (cliente.get("email") or "").strip().lower()
    if not email or "@" not in email:
        email = f"walkin.cliente{id_cliente}@iespro.local"
    elif fetch_one("SELECT id FROM usuarios WHERE LOWER(email) = %s", (email,)):
        email = f"walkin.cliente{id_cliente}@iespro.local"

    rol = fetch_one("SELECT id FROM roles WHERE nombre = 'CLIENTE'")
    id_rol = rol["id"] if rol else 5
    nombre = (cliente.get("nombre") or "Cliente").strip() or "Cliente"
    password = f"walkin{id_cliente:04d}"

    id_usuario = create_usuario({
        "nombre": nombre,
        "email": email,
        "password": password,
        "id_rol": id_rol,
        "id_sucursal": DEFAULT_SUCURSAL_ID,
        "es_cliente": 1,
        "es_trabajador": 0,
        "id_puesto": None,
    })
    execute("UPDATE clientes SET id_usuario = %s WHERE id = %s", (id_usuario, id_cliente))
    return id_usuario


def list_marcas() -> list[dict]:
    return fetch_all("SELECT id, nombre FROM marcas ORDER BY nombre")


def list_tipos_combustible() -> list[dict]:
    return fetch_all("SELECT id, nombre FROM tipos_combustible ORDER BY nombre")


def list_tipos_unidad() -> list[dict]:
    return fetch_all("SELECT id, nombre FROM tipos_unidad ORDER BY nombre")


def create_marca(nombre: str) -> int:
    return execute("INSERT IGNORE INTO marcas (nombre) VALUES (%s)", (nombre,))


def create_tipo_combustible(nombre: str) -> int:
    return execute("INSERT IGNORE INTO tipos_combustible (nombre) VALUES (%s)", (nombre,))


def create_tipo_unidad(nombre: str) -> int:
    return execute("INSERT IGNORE INTO tipos_unidad (nombre) VALUES (%s)", (nombre,))


def list_tipos_mantenimiento(id_sucursal: int) -> list[dict]:
    if id_sucursal:
        copiar_tipos_mantenimiento_plantilla(id_sucursal)
    return fetch_all(
        """
        SELECT id, nombre, descripcion, precio
        FROM tipos_mantenimiento
        WHERE id_sucursal = %s AND activo = 1
        ORDER BY nombre
        """,
        (id_sucursal,),
    )


def copiar_tipos_mantenimiento_plantilla(id_sucursal: int) -> None:
    """Copia el catálogo base a la sucursal si aún no tiene servicios."""
    if not id_sucursal:
        return
    existe = fetch_one(
        "SELECT id FROM tipos_mantenimiento WHERE id_sucursal = %s LIMIT 1",
        (id_sucursal,),
    )
    if existe:
        return
    plantillas = fetch_all(
        "SELECT nombre, descripcion, precio FROM tipos_mantenimiento_plantilla ORDER BY id"
    )
    for p in plantillas:
        execute(
            """
            INSERT INTO tipos_mantenimiento (nombre, descripcion, precio, id_sucursal)
            VALUES (%s, %s, %s, %s)
            """,
            (p["nombre"], p.get("descripcion"), p["precio"], id_sucursal),
        )


def create_tipo_mantenimiento(nombre: str, descripcion: str, precio: float, id_sucursal: int) -> int:
    return execute(
        """
        INSERT INTO tipos_mantenimiento (nombre, descripcion, precio, id_sucursal)
        VALUES (%s, %s, %s, %s)
        """,
        (nombre, descripcion, precio, id_sucursal),
    )
