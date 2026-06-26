"""Convierte resultados de tools en texto plano para el chat de la UI."""

from typing import Any


def _lines(items: list[str]) -> str:
    if not items:
        return ""
    return "\n".join(f"- {item}" for item in items)


def _error(result: Any) -> str | None:
    if isinstance(result, dict):
        if result.get("error"):
            return str(result["error"])
        if result.get("ok") is False and result.get("error"):
            return str(result["error"])
    return None


def format_tool_result(name: str, result: Any) -> str:
    err = _error(result)
    if err:
        return err

    if name == "listar_clientes" and isinstance(result, list):
        if not result:
            return "No hay clientes registrados."
        names = sorted({str(r.get("nombre", "")).strip() for r in result if r.get("nombre")})
        return f"Clientes registrados ({len(names)}):\n{_lines(names)}"

    if name == "listar_vehiculos" and isinstance(result, list):
        if not result:
            return "No hay vehículos registrados."
        items = []
        for r in result:
            placa = r.get("placa", "?")
            modelo = r.get("modelo", "")
            cliente = r.get("cliente", "")
            items.append(f"{placa} — {modelo} ({cliente})".strip())
        return f"Vehículos registrados ({len(items)}):\n{_lines(items)}"

    if name == "listar_citas" and isinstance(result, list):
        if not result:
            return "No hay citas registradas."
        items = []
        for r in result:
            cliente = r.get("cliente", "?")
            placa = r.get("placa", "?")
            estado = r.get("estado", "?")
            falla = r.get("descripcion_fallo", "")
            mecanico = r.get("mecanico", "")
            isla = r.get("isla", "")
            line = f"{cliente} | {placa} | {estado}"
            if falla:
                line += f" | {falla}"
            if mecanico:
                line += f" | {mecanico}"
            if isla:
                line += f" | {isla}"
            items.append(line)
        return f"Citas del taller ({len(items)}):\n{_lines(items)}"

    if name == "listar_mecanicos" and isinstance(result, list):
        if not result:
            return "No hay mecánicos disponibles."
        names = [str(r.get("nombre", "")).strip() for r in result if r.get("nombre")]
        return f"Mecánicos disponibles ({len(names)}):\n{_lines(names)}"

    if name == "listar_islas" and isinstance(result, list):
        if not result:
            return "No hay islas registradas."
        names = [str(r.get("nombre", "")).strip() for r in result if r.get("nombre")]
        return f"Islas del taller ({len(names)}):\n{_lines(names)}"

    if name == "mecanicos_en_isla" and isinstance(result, list):
        if not result:
            return "No hay mecánicos asignados a esa isla."
        names = [str(r.get("nombre", "")).strip() for r in result if r.get("nombre")]
        return f"Mecánicos en la isla ({len(names)}):\n{_lines(names)}"

    if name == "vehiculos_de_cliente" and isinstance(result, list):
        if not result:
            return "Ese cliente no tiene vehículos registrados."
        items = [f"{r.get('placa', '?')} — {r.get('modelo', '')}".strip() for r in result]
        return f"Vehículos del cliente ({len(items)}):\n{_lines(items)}"

    if name == "contar_citas" and isinstance(result, dict):
        total = result.get("total", 0)
        estado = result.get("estado")
        if estado:
            return f"Hay {total} citas con estado {estado}."
        return f"Hay {total} citas registradas en total."

    if name == "buscar_cliente" and isinstance(result, dict):
        if result.get("ok") and result.get("cliente"):
            c = result["cliente"]
            return f"Cliente encontrado: {c.get('nombre', '?')} (tel. {c.get('telefono', 'N/A')})"
        if result.get("coincidencias"):
            names = [c.get("nombre", "?") for c in result["coincidencias"]]
            return f"Varios clientes coinciden:\n{_lines(names)}"
        return result.get("error", "No encontré ese cliente.")

    if name == "buscar_vehiculo" and isinstance(result, dict):
        if result.get("ok") and result.get("vehiculo"):
            v = result["vehiculo"]
            return f"Vehículo: {v.get('placa', '?')} — {v.get('modelo', '')}"
        return result.get("error", "No encontré ese vehículo.")

    if name == "crear_cita_natural" and isinstance(result, dict):
        if result.get("ok"):
            return (
                f"Cita creada correctamente.\n"
                f"Cliente: {result.get('cliente', '?')}\n"
                f"Placa: {result.get('placa', '?')}\n"
                f"Mecánico: {result.get('mecanico', '?')}\n"
                f"Isla: {result.get('isla', '?')}"
            )
        return result.get("error", "No se pudo crear la cita.")

    if name in ("cambiar_estado_cita_natural", "cambiar_estado_cita") and isinstance(result, dict):
        if result.get("ok"):
            estado = result.get("nuevo_estado", result.get("estado", "?"))
            if estado == "CANCELADA":
                return (
                    "Cita cancelada. Quedó inactiva en el sistema "
                    f"(estado {estado}). No se eliminó el registro."
                )
            return f"Cita actualizada. Nuevo estado: {estado}."
        return result.get("error", "No se pudo cambiar el estado de la cita.")

    if name == "cancelar_cita_natural" and isinstance(result, dict):
        if result.get("ok"):
            return (
                "Cita cancelada correctamente. "
                "Quedó inactiva (estado CANCELADA); no se borró de la base de datos."
            )
        return result.get("error", "No se pudo cancelar la cita.")

    if name == "editar_cita_natural" and isinstance(result, dict):
        if result.get("ok"):
            cita = result.get("cita") or {}
            parts = [f"Cita de {result.get('placa', '?')} actualizada."]
            if cita.get("mecanico"):
                parts.append(f"Mecánico: {cita['mecanico']}.")
            if cita.get("isla"):
                parts.append(f"Isla: {cita['isla']}.")
            if cita.get("descripcion_fallo"):
                parts.append(f"Falla: {cita['descripcion_fallo']}.")
            return " ".join(parts)
        return result.get("error", "No se pudo editar la cita.")

    if name == "buscar_fallas_similares" and isinstance(result, dict):
        matches = result.get("matches", [])
        if not matches:
            return "No encontré fallas históricas similares."
        items = []
        for m in matches[:5]:
            placa = m.get("placa", "?")
            texto = m.get("texto", "")
            items.append(f"{placa}: {texto}")
        return f"Casos parecidos encontrados:\n{_lines(items)}"

    return ""


def format_tool_calls_log(tool_calls: list[dict]) -> str:
    parts = []
    for tc in tool_calls:
        text = format_tool_result(tc.get("name", ""), tc.get("result"))
        if text:
            parts.append(text)
    return "\n\n".join(parts).strip()
