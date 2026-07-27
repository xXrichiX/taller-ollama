export interface User {
  id: number;
  nombre: string;
  email: string;
  rol_nombre: string;
  puesto_nombre?: string;
  sucursales_ids: number[];
  id_sucursal?: number | null;
  id_isla?: number | null;
  id_cliente?: number | null;
}

export interface Permissions {
  is_admin: boolean;
  is_propietario: boolean;
  is_mecanico: boolean;
  is_cliente: boolean;
  is_staff: boolean;
  needs_taller_setup: boolean;
  can_create_sucursal: boolean;
  can_manage_branch: boolean;
  can_manage_citas: boolean;
  can_create_citas: boolean;
  can_manage_usuarios: boolean;
  show_isla_picker: boolean;
  show_taller_module: boolean;
}

export interface AuthState {
  token: string;
  user: User;
  role_label: string;
  permissions: Permissions;
}
