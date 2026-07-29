import type { Permissions, User } from "../types";

export type AccountUi = {
  isla_picker?: boolean;
  workshop_module?: boolean;
  needs_setup?: boolean;
  can_add_branch?: boolean;
};

/** Reconstruye permisos de UI sin depender del objeto permissions del API en producción. */
export function derivePermissions(
  user: User,
  profile: string,
  ui: AccountUi = {},
): Permissions {
  const is_cliente = profile === "client";
  const is_propietario = profile === "owner";
  const is_mecanico = profile === "mechanic";
  const is_staff = is_propietario || is_mecanico || profile === "staff";
  const needs_setup = ui.needs_setup ?? false;

  return {
    is_admin: false,
    is_propietario,
    is_mecanico,
    is_cliente,
    is_staff,
    needs_taller_setup: needs_setup,
    can_create_sucursal: ui.can_add_branch ?? is_propietario,
    can_manage_branch: is_propietario,
    can_manage_citas: is_staff && !needs_setup,
    can_create_citas: (is_propietario || is_mecanico || is_cliente) && !needs_setup,
    can_manage_usuarios: false,
    show_isla_picker: ui.isla_picker ?? false,
    show_taller_module: ui.workshop_module ?? false,
  };
}
