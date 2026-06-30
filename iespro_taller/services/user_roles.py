"""Roles y permisos de usuario.

Rol  = qué puede hacer en el sistema (permisos).
Puesto = cargo en el taller (informativo / asignación operativa), NO define permisos.

Ejemplo: alguien con puesto «Mecánico» puede tener rol ADMIN y administrar toda la sucursal.
         Alguien con rol MECANICO solo gestiona sus citas asignadas, aunque su puesto sea otro.
"""

SUPER_ADMIN_ROLES = frozenset({"SUPER_ADMIN"})
BRANCH_ADMIN_ROLES = frozenset({"ADMIN", "JEFE_TALLER"})
STAFF_MANAGE_ROLES = SUPER_ADMIN_ROLES | BRANCH_ADMIN_ROLES
WORKSHOP_STAFF_ROLES = STAFF_MANAGE_ROLES | frozenset({"MECANICO"})
PENDING_ROLES = frozenset({"PENDIENTE"})

# Puestos visibles al asignar personal del taller.
PUESTOS_STAFF_UI = frozenset({"Admin", "Mecánico"})

# Puestos que pueden recibir vehículos/citas en el piso del taller.
PUESTOS_MECANICO_ASIGNABLE = frozenset({"Mecánico"})


def _norm(rol_nombre: str | None) -> str:
    return (rol_nombre or "").upper()


def is_super_admin(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in SUPER_ADMIN_ROLES


def is_branch_admin(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in BRANCH_ADMIN_ROLES


def is_cliente(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) == "CLIENTE"


def is_mecanico(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) == "MECANICO"


def is_pending(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in PENDING_ROLES


def is_staff_manager(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in STAFF_MANAGE_ROLES


def is_workshop_staff(rol_nombre: str | None) -> bool:
    return _norm(rol_nombre) in WORKSHOP_STAFF_ROLES


def can_manage_branch(rol_nombre: str | None) -> bool:
    """Admin de sucursal o superior."""
    return is_super_admin(rol_nombre) or is_branch_admin(rol_nombre)


def flags_for_role(rol_nombre: str | None) -> tuple[int, int]:
    """Deriva (es_cliente, es_trabajador) desde el rol. El puesto no interviene."""
    rol = _norm(rol_nombre)
    if rol == "CLIENTE":
        return 1, 0
    if rol in WORKSHOP_STAFF_ROLES | SUPER_ADMIN_ROLES:
        return 0, 1
    return 0, 0


def can_assign_work_as_mecanico(rol_nombre: str | None, puesto_nombre: str | None = None) -> bool:
    """¿Puede aparecer en listas de asignación de vehículos/citas en el taller?"""
    if is_mecanico(rol_nombre):
        return True
    if puesto_nombre and puesto_nombre in PUESTOS_MECANICO_ASIGNABLE:
        return True
    p = (puesto_nombre or "").lower()
    return "mecanico" in p or "mecánico" in p
