from typing import Any

from config import DEFAULT_SUCURSAL_ID
from db.connection import execute, fetch_all, fetch_one


def login(email: str, password: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT u.*, r.nombre AS rol_nombre, p.nombre AS puesto_nombre
        FROM usuarios u
        JOIN roles r ON r.id = u.id_rol
        LEFT JOIN puestos p ON p.id = u.id_puesto
        WHERE u.email = %s AND u.password = %s AND u.activo = 1
        """,
        (email, password),
    )


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


def assign_usuario_staff(id_usuario: int, id_puesto: int, puesto_nombre: str) -> dict[str, Any]:
    """Asigna puesto en el taller y el rol de sistema correspondiente."""
    id_rol, rol_nombre = rol_from_puesto(puesto_nombre)
    update_usuario_puesto(id_usuario, id_puesto)
    return update_usuario_rol(id_usuario, id_rol, rol_nombre)


def list_usuarios(id_sucursal: int | None = None) -> list[dict]:
    query = """
        SELECT u.id, u.nombre, u.email, r.nombre AS rol, s.nombre AS sucursal,
               p.nombre AS puesto, u.activo, u.id_sucursal, u.id_rol
        FROM usuarios u
        JOIN roles r ON r.id = u.id_rol
        LEFT JOIN sucursales s ON s.id = u.id_sucursal
        LEFT JOIN puestos p ON p.id = u.id_puesto
        WHERE 1=1
    """
    params: list[Any] = []
    if id_sucursal:
        query += " AND u.id_sucursal = %s"
        params.append(id_sucursal)
    query += " ORDER BY u.id"
    return fetch_all(query, tuple(params))


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


def create_sucursal(nombre: str, direccion: str = "") -> int:
    return execute(
        "INSERT INTO sucursales (nombre, direccion) VALUES (%s, %s)",
        (nombre.strip(), direccion.strip()),
    )


def update_sucursal(id_sucursal: int, nombre: str, direccion: str, activo: bool = True) -> dict[str, Any]:
    execute(
        "UPDATE sucursales SET nombre = %s, direccion = %s, activo = %s WHERE id = %s",
        (nombre.strip(), direccion.strip(), int(activo), id_sucursal),
    )
    return {"ok": True}


def get_sucursal(id_sucursal: int) -> dict | None:
    return fetch_one("SELECT id, nombre, direccion, activo FROM sucursales WHERE id = %s", (id_sucursal,))


def register_usuario(
    nombre: str,
    email: str,
    password: str,
    codigo_invitacion: str,
) -> dict[str, Any]:
    """Registro público con código de invitación. Rol PENDIENTE hasta que un admin lo asigne."""
    from services.invitation_service import consumir_codigo, validar_codigo
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

    inv = validar_codigo(codigo_invitacion)
    if not inv.get("ok"):
        return inv

    rol = fetch_one("SELECT id FROM roles WHERE nombre = 'PENDIENTE'")
    id_rol = rol["id"] if rol else 6

    id_usuario = create_usuario({
        "nombre": nombre,
        "email": email,
        "password": password,
        "id_rol": id_rol,
        "id_sucursal": inv["id_sucursal"],
        "es_cliente": 0,
        "es_trabajador": 0,
        "id_puesto": None,
    })
    consumir_codigo(inv["id_codigo"])
    return {
        "ok": True,
        "id_usuario": id_usuario,
        "sucursal": inv.get("sucursal_nombre"),
        "pendiente_rol": True,
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
    return fetch_all(
        """
        SELECT id, nombre, descripcion, precio
        FROM tipos_mantenimiento
        WHERE id_sucursal = %s AND activo = 1
        ORDER BY nombre
        """,
        (id_sucursal,),
    )


def create_tipo_mantenimiento(nombre: str, descripcion: str, precio: float, id_sucursal: int) -> int:
    return execute(
        """
        INSERT INTO tipos_mantenimiento (nombre, descripcion, precio, id_sucursal)
        VALUES (%s, %s, %s, %s)
        """,
        (nombre, descripcion, precio, id_sucursal),
    )
