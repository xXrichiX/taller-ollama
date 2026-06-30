from typing import Any

from config import DEFAULT_SUCURSAL_ID
from db.connection import execute, fetch_all, fetch_one


def login(email: str, password: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT u.*, r.nombre AS rol_nombre
        FROM usuarios u
        JOIN roles r ON r.id = u.id_rol
        WHERE u.email = %s AND u.password = %s AND u.activo = 1
        """,
        (email, password),
    )


def list_sucursales() -> list[dict]:
    return fetch_all("SELECT id, nombre FROM sucursales WHERE activo = 1 ORDER BY nombre")


def list_roles() -> list[dict]:
    return fetch_all("SELECT id, nombre FROM roles ORDER BY id")


def list_puestos() -> list[dict]:
    return fetch_all("SELECT id, nombre FROM puestos ORDER BY nombre")


def list_usuarios() -> list[dict]:
    return fetch_all(
        """
        SELECT u.id, u.nombre, u.email, r.nombre AS rol, s.nombre AS sucursal,
               u.es_cliente, u.es_trabajador, u.activo
        FROM usuarios u
        JOIN roles r ON r.id = u.id_rol
        LEFT JOIN sucursales s ON s.id = u.id_sucursal
        ORDER BY u.id
        """
    )


def register_usuario(nombre: str, email: str, password: str, id_sucursal: int = DEFAULT_SUCURSAL_ID) -> dict[str, Any]:
    """Registro público: crea usuario CLIENTE y ficha en clientes."""
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

    rol = fetch_one("SELECT id FROM roles WHERE nombre = 'CLIENTE'")
    id_rol = rol["id"] if rol else 4

    id_usuario = create_usuario({
        "nombre": nombre,
        "email": email,
        "password": password,
        "id_rol": id_rol,
        "id_sucursal": id_sucursal,
        "es_cliente": 1,
        "es_trabajador": 0,
        "id_puesto": None,
    })
    create_cliente(nombre, "", email, id_usuario)
    return {"ok": True, "id_usuario": id_usuario}


def create_usuario(data: dict) -> int:
    return execute(
        """
        INSERT INTO usuarios (nombre, email, password, id_rol, id_sucursal, es_cliente, es_trabajador, id_puesto)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            data["nombre"], data["email"], data["password"], data["id_rol"],
            data.get("id_sucursal"), data["es_cliente"], data["es_trabajador"],
            data.get("id_puesto"),
        ),
    )


def list_clientes() -> list[dict]:
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
    id_rol = rol["id"] if rol else 4
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
