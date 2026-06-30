"""Roles y permisos — solo Admin y Mecánico en el taller."""

ADMIN_ROLES = frozenset({"ADMIN", "SUPER_ADMIN"})
WORKSHOP_STAFF_ROLES = ADMIN_ROLES | frozenset({"MECANICO"})
PENDING_ROLES = frozenset({"PENDIENTE"})

PUESTOS_STAFF_UI = frozenset({"Admin", "Mecánico"})
PUESTOS_MECANICO_ASIGNABLE = frozenset({"Mecánico"})


def _norm(rol_nombre: str | None) -> str:
    return (rol_nombre or "").upper()


def is_admin(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in ADMIN_ROLES


def is_super_admin(rol_nombre: str | None) -> bool:
    """Alias de is_admin (compatibilidad)."""
    return is_admin(rol_nombre)


def is_branch_admin(rol_nombre: str | None) -> bool:
    return is_admin(rol_nombre)


def is_cliente(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) == "CLIENTE"


def is_mecanico(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) == "MECANICO"


def is_pending(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in PENDING_ROLES


def is_staff_manager(rol_nombre: str | None) -> bool:
    """Solo el admin gestiona usuarios."""
    return is_admin(rol_nombre)


def is_workshop_staff(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in WORKSHOP_STAFF_ROLES


def can_manage_branch(rol_nombre: str | None) -> bool:
    return is_admin(rol_nombre)


def flags_for_role(rol_nombre: str | None) -> tuple[int, int]:
    rol = _norm(rol_nombre)
    if rol == "CLIENTE":
        return 1, 0
    if rol in WORKSHOP_STAFF_ROLES:
        return 0, 1
    return 0, 0


def can_assign_work_as_mecanico(rol_nombre: str | None, puesto_nombre: str | None = None) -> bool:
    if is_mecanico(rol_nombre):
        return True
    if puesto_nombre and puesto_nombre in PUESTOS_MECANICO_ASIGNABLE:
        return True
    p = (puesto_nombre or "").lower()
    return "mecanico" in p or "mecánico" in p
