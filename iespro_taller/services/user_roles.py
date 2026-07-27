"""Roles — Mecánico (taller, permisos completos) y Cliente."""

# Nombres legacy: mismos permisos que MECANICO (migración de BD antiguas).
WORKSHOP_ROLES = frozenset({"MECANICO", "ADMIN", "SUPER_ADMIN"})
PUESTOS_MECANICO = frozenset({"Mecánico"})


def _norm(rol_nombre: str | None) -> str:
    return (rol_nombre or "").upper()


def is_admin(rol_nombre: str | None) -> bool:
    """Deprecated: ya no hay rol admin separado."""
    return False


def is_super_admin(rol_nombre: str | None) -> bool:
    return False


def is_branch_admin(rol_nombre: str | None) -> bool:
    return is_workshop_staff(rol_nombre)


def is_cliente(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) == "CLIENTE"


def is_mecanico(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in WORKSHOP_ROLES


def is_pending(rol_nombre: str | None) -> bool:
    return False


def is_staff_manager(rol_nombre: str | None) -> bool:
    """Personal del taller con acceso completo a su sucursal."""
    return is_workshop_staff(rol_nombre)


def is_workshop_staff(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in WORKSHOP_ROLES


def can_manage_branch(rol_nombre: str | None) -> bool:
    return is_workshop_staff(rol_nombre)


def flags_for_role(rol_nombre: str | None) -> tuple[int, int]:
    rol = _norm(rol_nombre)
    if rol == "CLIENTE":
        return 1, 0
    if rol in WORKSHOP_ROLES:
        return 0, 1
    return 0, 0


def role_display_label(rol_nombre: str | None, *, es_propietario: bool = False) -> str:
    """Etiqueta visible en la app."""
    if is_cliente(rol_nombre):
        return "Cliente"
    if is_workshop_staff(rol_nombre):
        return "Dueño del taller" if es_propietario else "Mecánico"
    return rol_nombre or ""


def can_assign_work_as_mecanico(rol_nombre: str | None, puesto_nombre: str | None = None) -> bool:
    if is_workshop_staff(rol_nombre):
        return True
    p = (puesto_nombre or "").lower()
    return "mecanico" in p or "mecánico" in p
