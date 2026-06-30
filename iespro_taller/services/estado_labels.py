"""Etiquetas legibles para estados de citas."""

ESTADO_A_ETIQUETA = {
    "PENDIENTE": "Pendiente",
    "EN_PROCESO": "En proceso",
    "COMPLETADA": "Completada",
    "CANCELADA": "Cancelada",
}

ETIQUETA_A_ESTADO = {v: k for k, v in ESTADO_A_ETIQUETA.items()}

ESTADOS_UI = list(ESTADO_A_ETIQUETA.values())


def estado_a_etiqueta(estado: str | None) -> str:
    return ESTADO_A_ETIQUETA.get((estado or "").upper(), estado or "")


def etiqueta_a_estado(etiqueta: str) -> str | None:
    return ETIQUETA_A_ESTADO.get(etiqueta)
