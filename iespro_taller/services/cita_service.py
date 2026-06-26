import re
import unicodedata
from datetime import date, datetime
from typing import Any

from db.connection import execute, fetch_all, fetch_one


def _norm_text(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text.lower().strip())


def _norm_placa(placa: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _norm_text(placa))


def find_cliente_by_nombre(nombre: str) -> dict:
    clientes = fetch_all("SELECT id, nombre FROM clientes ORDER BY nombre")
    norm = _norm_text(nombre)
    exact = [c for c in clientes if _norm_text(c["nombre"]) == norm]
    if len(exact) == 1:
        return {"ok": True, "cliente": exact[0]}
    partial = [
        c for c in clientes
        if norm in _norm_text(c["nombre"])
        or all(part in _norm_text(c["nombre"]) for part in norm.split() if len(part) > 2)
    ]
    if len(partial) == 1:
        return {"ok": True, "cliente": partial[0]}
    if not partial:
        return {"ok": False, "error": f"No encontré cliente con nombre '{nombre}'."}
    return {
        "ok": False,
        "error": f"Hay {len(partial)} clientes que coinciden con '{nombre}'.",
        "coincidencias": partial,
    }


def find_vehiculo_por_referencia(
    placa: str | None = None,
    id_cliente: int | None = None,
    modelo: str | None = None,
) -> dict:
    vehiculos = list_vehiculos(id_cliente)
    if placa:
        norm_placa = _norm_placa(placa)
        matches = [v for v in vehiculos if _norm_placa(v["placa"]) == norm_placa]
        if len(matches) == 1:
            return {"ok": True, "vehiculo": matches[0]}
        if not matches:
            return {"ok": False, "error": f"No encontré vehículo con placa '{placa}'."}
        return {
            "ok": False,
            "error": f"Hay {len(matches)} vehículos con placa '{placa}'.",
            "coincidencias": matches,
        }

    if modelo:
        norm_modelo = _norm_text(modelo)
        matches = [v for v in vehiculos if norm_modelo in _norm_text(v.get("modelo") or "")]
        if len(matches) == 1:
            return {"ok": True, "vehiculo": matches[0]}
        if not matches:
            return {"ok": False, "error": f"No encontré vehículo con modelo '{modelo}'."}
        return {
            "ok": False,
            "error": f"Hay {len(matches)} vehículos con modelo '{modelo}'.",
            "coincidencias": matches,
        }

    return {"ok": False, "error": "Indica placa o modelo del vehículo."}


def find_mecanico_by_nombre(nombre: str, id_sucursal: int) -> dict:
    mecanicos = list_mecanicos(id_sucursal)
    norm = _norm_text(nombre)
    exact = [m for m in mecanicos if _norm_text(m["nombre"]) == norm]
    if len(exact) == 1:
        return {"ok": True, "mecanico": exact[0]}
    partial = [
        m for m in mecanicos
        if norm in _norm_text(m["nombre"])
        or any(part in _norm_text(m["nombre"]) for part in norm.split() if len(part) > 2)
    ]
    if len(partial) == 1:
        return {"ok": True, "mecanico": partial[0]}
    if not partial:
        return {"ok": False, "error": f"No encontré mecánico '{nombre}'."}
    return {
        "ok": False,
        "error": f"Hay {len(partial)} mecánicos que coinciden con '{nombre}'.",
        "coincidencias": partial,
    }


def find_isla_by_referencia(referencia: str, id_sucursal: int) -> dict:
    islas = list_islas(id_sucursal)
    if not islas:
        return {"ok": False, "error": f"No hay islas en la sucursal {id_sucursal}."}

    ref = _norm_text(referencia)
    digits = re.findall(r"\d+", ref)
    if digits:
        num = digits[0]
        by_num = [
            i for i in islas
            if str(i["id"]) == num or num in _norm_text(i["nombre"])
        ]
        if len(by_num) == 1:
            return {"ok": True, "isla": by_num[0]}

    exact = [i for i in islas if _norm_text(i["nombre"]) == ref]
    if len(exact) == 1:
        return {"ok": True, "isla": exact[0]}

    partial = [i for i in islas if ref in _norm_text(i["nombre"])]
    if len(partial) == 1:
        return {"ok": True, "isla": partial[0]}
    if not partial:
        return {"ok": False, "error": f"No encontré isla '{referencia}'."}
    return {
        "ok": False,
        "error": f"Hay {len(partial)} islas que coinciden con '{referencia}'.",
        "coincidencias": partial,
    }


def find_cita_activa_por_placa(placa: str, id_sucursal: int | None = None) -> dict:
    query = """
        SELECT c.id, c.estado, cl.nombre AS cliente, v.placa, c.descripcion_fallo
        FROM citas c
        JOIN clientes cl ON cl.id = c.id_cliente
        JOIN vehiculos v ON v.id = c.id_vehiculo
        WHERE REPLACE(LOWER(v.placa), '-', '') = %s
          AND c.estado IN ('PENDIENTE', 'EN_PROCESO')
    """
    params: list[Any] = [_norm_placa(placa)]
    if id_sucursal:
        query += " AND c.id_sucursal = %s"
        params.append(id_sucursal)
    query += " ORDER BY c.fecha_cita DESC LIMIT 5"
    citas = fetch_all(query, tuple(params))
    if not citas:
        return {"ok": False, "error": f"No hay cita activa para la placa '{placa}'."}
    if len(citas) == 1:
        return {"ok": True, "cita": citas[0]}
    return {
        "ok": False,
        "error": f"Hay {len(citas)} citas activas para '{placa}'. Indica id_cita.",
        "coincidencias": citas,
    }


def list_vehiculos(id_cliente: int | None = None) -> list[dict]:
    query = """
        SELECT v.id, v.numero_economico, v.placa, v.modelo, m.nombre AS marca,
               c.nombre AS cliente, v.kilometraje, v.activo
        FROM vehiculos v
        JOIN marcas m ON m.id = v.id_marca
        JOIN clientes c ON c.id = v.id_cliente
    """
    params: tuple = ()
    if id_cliente:
        query += " WHERE v.id_cliente = %s"
        params = (id_cliente,)
    query += " ORDER BY v.id DESC"
    return fetch_all(query, params)


def list_vehiculos_por_usuario(id_usuario: int) -> list[dict]:
    return fetch_all(
        """
        SELECT v.id, v.placa, v.modelo, m.nombre AS marca
        FROM vehiculos v
        JOIN marcas m ON m.id = v.id_marca
        WHERE v.id_usuario = %s AND v.activo = 1
        ORDER BY v.placa
        """,
        (id_usuario,),
    )


def create_vehiculo(data: dict) -> int:
    return execute(
        """
        INSERT INTO vehiculos (
            numero_economico, placa, serie, id_marca, modelo,
            id_tipo_combustible, id_tipo_unidad, kilometraje, dias_mantenimiento,
            observaciones, id_cliente, id_usuario
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data["numero_economico"], data["placa"], data["serie"], data["id_marca"],
            data["modelo"], data["id_tipo_combustible"], data["id_tipo_unidad"],
            data["kilometraje"], data["dias_mantenimiento"], data.get("observaciones"),
            data["id_cliente"], data["id_usuario"],
        ),
    )


def get_mi_taller(id_sucursal: int) -> dict | None:
    row = fetch_one("SELECT id, nombre FROM mi_taller WHERE id_sucursal = %s", (id_sucursal,))
    if row:
        return row
    taller_id = execute(
        "INSERT INTO mi_taller (nombre, id_sucursal) VALUES (%s, %s)",
        (f"Taller Sucursal {id_sucursal}", id_sucursal),
    )
    return fetch_one("SELECT id, nombre FROM mi_taller WHERE id = %s", (taller_id,))


def list_islas(id_sucursal: int) -> list[dict]:
    taller = get_mi_taller(id_sucursal)
    if not taller:
        return []
    return fetch_all(
        "SELECT id, nombre, activo FROM islas WHERE id_mi_taller = %s ORDER BY nombre",
        (taller["id"],),
    )


def create_isla(nombre: str, id_sucursal: int) -> int:
    taller = get_mi_taller(id_sucursal)
    return execute(
        "INSERT INTO islas (nombre, id_mi_taller) VALUES (%s, %s)",
        (nombre, taller["id"]),
    )


def list_mecanicos(id_sucursal: int) -> list[dict]:
    return fetch_all(
        """
        SELECT u.id, u.nombre
        FROM usuarios u
        JOIN roles r ON r.id = u.id_rol
        WHERE u.es_trabajador = 1 AND u.activo = 1
          AND (u.id_sucursal = %s OR u.id_sucursal IS NULL)
          AND r.nombre IN ('MECANICO', 'JEFE_TALLER', 'ADMIN')
        ORDER BY u.nombre
        """,
        (id_sucursal,),
    )


def assign_mecanico_isla(id_isla: int, id_usuario: int, es_responsable: bool = False) -> None:
    execute(
        """
        INSERT INTO isla_mecanicos (id_isla, id_usuario, es_responsable)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE es_responsable = VALUES(es_responsable)
        """,
        (id_isla, id_usuario, int(es_responsable)),
    )


def list_isla_mecanicos(id_isla: int) -> list[dict]:
    return fetch_all(
        """
        SELECT im.id, u.nombre, im.es_responsable
        FROM isla_mecanicos im
        JOIN usuarios u ON u.id = im.id_usuario
        WHERE im.id_isla = %s
        ORDER BY im.es_responsable DESC, u.nombre
        """,
        (id_isla,),
    )


def list_horarios_disponibles(fecha: str, id_sucursal: int) -> list[dict]:
    return fetch_all(
        """
        SELECT id, fecha, hora, disponible
        FROM horarios
        WHERE fecha = %s AND id_sucursal = %s AND disponible = 1
        ORDER BY hora
        """,
        (fecha, id_sucursal),
    )


def list_citas(id_sucursal: int | None = None) -> list[dict]:
    query = """
        SELECT c.id, cl.nombre AS cliente, v.placa, v.modelo,
               c.fecha_cita, c.descripcion_fallo, c.estado,
               u.nombre AS mecanico, i.nombre AS isla,
               c.fecha_compromiso, c.hora_compromiso
        FROM citas c
        JOIN clientes cl ON cl.id = c.id_cliente
        JOIN vehiculos v ON v.id = c.id_vehiculo
        JOIN usuarios u ON u.id = c.id_mecanico
        JOIN islas i ON i.id = c.id_isla
    """
    params: tuple = ()
    if id_sucursal:
        query += " WHERE c.id_sucursal = %s"
        params = (id_sucursal,)
    query += " ORDER BY c.fecha_cita DESC"
    return fetch_all(query, params)


def create_cita(data: dict, servicio_ids: list[int]) -> int:
    cliente = fetch_one("SELECT id FROM clientes WHERE id = %s", (data["id_cliente"],))
    if not cliente:
        raise ValueError("El cliente no existe en la tabla clientes.")

    vehiculo = fetch_one(
        "SELECT id FROM vehiculos WHERE id = %s AND id_cliente = %s",
        (data["id_vehiculo"], data["id_cliente"]),
    )
    if not vehiculo:
        raise ValueError("El vehículo no pertenece al cliente seleccionado.")

    cita_id = execute(
        """
        INSERT INTO citas (
            id_cliente, id_vehiculo, id_sucursal, fecha_cita, id_horario,
            id_mecanico, id_isla, descripcion_fallo, fecha_compromiso, hora_compromiso, estado
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDIENTE')
        """,
        (
            data["id_cliente"], data["id_vehiculo"], data["id_sucursal"],
            data["fecha_cita"], data.get("id_horario"), data["id_mecanico"],
            data["id_isla"], data["descripcion_fallo"], data["fecha_compromiso"],
            data["hora_compromiso"],
        ),
    )

    if data.get("id_horario"):
        execute("UPDATE horarios SET disponible = 0 WHERE id = %s", (data["id_horario"],))

    for sid in servicio_ids:
        execute(
            "INSERT INTO cita_servicios (id_cita, id_tipo_mantenimiento) VALUES (%s, %s)",
            (cita_id, sid),
        )

    execute(
        """
        INSERT INTO fallas_registradas (id_cita, id_vehiculo, descripcion)
        VALUES (%s, %s, %s)
        """,
        (cita_id, data["id_vehiculo"], data["descripcion_fallo"]),
    )

    return cita_id


def get_cita_by_id(id_cita: int) -> dict | None:
    return fetch_one(
        """
        SELECT c.id, c.estado, c.descripcion_fallo, c.fecha_cita, c.id_horario,
               cl.nombre AS cliente, v.placa, u.nombre AS mecanico, i.nombre AS isla
        FROM citas c
        JOIN clientes cl ON cl.id = c.id_cliente
        JOIN vehiculos v ON v.id = c.id_vehiculo
        JOIN usuarios u ON u.id = c.id_mecanico
        JOIN islas i ON i.id = c.id_isla
        WHERE c.id = %s
        """,
        (id_cita,),
    )


def cancelar_cita(id_cita: int) -> dict:
    cita = fetch_one(
        "SELECT id, id_horario, estado FROM citas WHERE id = %s",
        (id_cita,),
    )
    if not cita:
        return {"ok": False, "error": "Cita no encontrada."}
    if cita["estado"] == "CANCELADA":
        return {"ok": False, "error": "La cita ya está cancelada (inactiva)."}
    if cita["estado"] == "COMPLETADA":
        return {"ok": False, "error": "No se puede cancelar una cita ya completada."}

    execute("UPDATE citas SET estado = 'CANCELADA' WHERE id = %s", (id_cita,))
    if cita.get("id_horario"):
        execute("UPDATE horarios SET disponible = 1 WHERE id = %s", (cita["id_horario"],))

    return {
        "ok": True,
        "id_cita": id_cita,
        "nuevo_estado": "CANCELADA",
        "mensaje": "Cita cancelada. Quedó inactiva en el sistema (no se eliminó el registro).",
    }


def update_cita(id_cita: int, updates: dict) -> dict:
    cita = fetch_one(
        """
        SELECT c.id, c.estado, v.placa
        FROM citas c
        JOIN vehiculos v ON v.id = c.id_vehiculo
        WHERE c.id = %s
        """,
        (id_cita,),
    )
    if not cita:
        return {"ok": False, "error": "Cita no encontrada."}
    if cita["estado"] in ("CANCELADA", "COMPLETADA"):
        return {
            "ok": False,
            "error": f"No se puede editar una cita con estado {cita['estado']}.",
        }

    set_clauses: list[str] = []
    params: list[Any] = []

    field_map = {
        "descripcion_fallo": "descripcion_fallo",
        "id_mecanico": "id_mecanico",
        "id_isla": "id_isla",
        "fecha_cita": "fecha_cita",
        "fecha_compromiso": "fecha_compromiso",
        "hora_compromiso": "hora_compromiso",
        "estado": "estado",
    }
    for key, column in field_map.items():
        if key in updates and updates[key] is not None:
            set_clauses.append(f"{column} = %s")
            params.append(updates[key])

    if not set_clauses:
        return {"ok": False, "error": "Indica qué quieres cambiar (falla, mecánico, isla, fecha, etc.)."}

    params.append(id_cita)
    execute(f"UPDATE citas SET {', '.join(set_clauses)} WHERE id = %s", tuple(params))

    if updates.get("descripcion_fallo"):
        execute(
            "UPDATE fallas_registradas SET descripcion = %s WHERE id_cita = %s",
            (updates["descripcion_fallo"], id_cita),
        )

    refreshed = get_cita_by_id(id_cita)
    return {
        "ok": True,
        "id_cita": id_cita,
        "placa": cita["placa"],
        "cita": refreshed,
        "mensaje": "Cita actualizada correctamente.",
    }


def count_citas(estado: str | None = None, id_sucursal: int | None = None) -> int:
    query = "SELECT COUNT(*) AS total FROM citas WHERE 1=1"
    params: list[Any] = []
    if estado:
        query += " AND estado = %s"
        params.append(estado)
    if id_sucursal:
        query += " AND id_sucursal = %s"
        params.append(id_sucursal)
    row = fetch_one(query, tuple(params))
    return int(row["total"]) if row else 0


def get_mecanicos_por_isla(id_isla: int) -> list[dict]:
    return fetch_all(
        """
        SELECT u.id, u.nombre, im.es_responsable
        FROM isla_mecanicos im
        JOIN usuarios u ON u.id = im.id_usuario
        WHERE im.id_isla = %s
        ORDER BY im.es_responsable DESC
        """,
        (id_isla,),
    )


def list_fallas() -> list[dict]:
    return fetch_all(
        """
        SELECT f.id, f.descripcion, f.diagnostico, f.resuelto,
               v.placa, c.id AS id_cita
        FROM fallas_registradas f
        JOIN vehiculos v ON v.id = f.id_vehiculo
        LEFT JOIN citas c ON c.id = f.id_cita
        ORDER BY f.registrado_en DESC
        """
    )
