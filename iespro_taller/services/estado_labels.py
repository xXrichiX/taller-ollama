"""Etiquetas legibles para estados de órdenes de trabajo (citas)."""

ESTADO_A_ETIQUETA = {
    "PENDIENTE": "Pendiente",
    "RECIBIDO": "Recibido",
    "DIAGNOSTICO": "Diagnóstico",
    "EN_PROCESO": "En proceso",
    "EN_REPARACION": "En reparación",
    "ESPERANDO_REFACCIONES": "Esperando refacciones",
    "COMPLETADA": "Completada",
    "FINALIZADO": "Finalizado",
    "CANCELADA": "Cancelada",
}

ETIQUETA_A_ESTADO = {v: k for k, v in ESTADO_A_ETIQUETA.items()}

ESTADOS_UI = [
    "Recibido",
    "Diagnóstico",
    "En reparación",
    "Esperando refacciones",
    "En proceso",
    "Pendiente",
    "Finalizado",
    "Completada",
    "Cancelada",
]

ESTADOS_MECANICO_UI = [
    "Recibido",
    "Diagnóstico",
    "En reparación",
    "Esperando refacciones",
    "En proceso",
    "Finalizado",
]

ESTADOS_ACTIVOS = frozenset({
    "PENDIENTE", "RECIBIDO", "DIAGNOSTICO", "EN_PROCESO",
    "EN_REPARACION", "ESPERANDO_REFACCIONES",
})

ESTADOS_FINALIZADOS = frozenset({"COMPLETADA", "FINALIZADO", "CANCELADA"})


def estado_a_etiqueta(estado: str | None) -> str:
    return ESTADO_A_ETIQUETA.get((estado or "").upper(), estado or "")


def etiqueta_a_estado(etiqueta: str) -> str | None:
    return ETIQUETA_A_ESTADO.get(etiqueta)
