"""Roles y permisos de usuario."""

STAFF_MANAGE_ROLES = frozenset({"ADMIN", "JEFE_TALLER"})
WORKSHOP_STAFF_ROLES = frozenset({"ADMIN", "JEFE_TALLER", "MECANICO"})


def is_cliente(rol_nombre: str | None) -> bool:
    return (rol_nombre or "").upper() == "CLIENTE"


def is_mecanico(rol_nombre: str | None) -> bool:
    return (rol_nombre or "").upper() == "MECANICO"


def is_staff_manager(rol_nombre: str | None) -> bool:
    return (rol_nombre or "").upper() in STAFF_MANAGE_ROLES


def is_workshop_staff(rol_nombre: str | None) -> bool:
    return (rol_nombre or "").upper() in WORKSHOP_STAFF_ROLES
