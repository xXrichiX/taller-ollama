import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, getStoredToken, setStoredToken } from "../api/client";
import type { AuthState, Permissions, User } from "../types";

interface AuthContextValue {
  auth: AuthState | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (nombre: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  setSucursal: (id: number) => Promise<void>;
  setIsla: (id: number) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const defaultPerms: Permissions = {
  is_admin: false,
  is_propietario: false,
  is_mecanico: false,
  is_cliente: false,
  is_staff: false,
  needs_taller_setup: false,
  can_create_sucursal: false,
  can_manage_branch: false,
  can_manage_citas: false,
  can_create_citas: false,
  can_manage_usuarios: false,
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async (token: string) => {
    const data = await api<{
      user: User;
      role_label: string;
      permissions: Permissions;
    }>("/api/auth/me", {}, token);
    setAuth({
      token,
      user: data.user,
      role_label: data.role_label,
      permissions: data.permissions,
    });
  }, []);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }
    loadMe(token)
      .catch(() => setStoredToken(null))
      .finally(() => setLoading(false));
  }, [loadMe]);

  const login = async (email: string, password: string) => {
    const data = await api<{
      token: string;
      user: User;
      role_label: string;
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setStoredToken(data.token);
    await loadMe(data.token);
  };

  const register = async (nombre: string, email: string, password: string) => {
    const data = await api<{
      token?: string;
      user?: User;
      ok?: boolean;
      message?: string;
    }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ nombre, email, password }),
    });
    if (data.token && data.user) {
      setStoredToken(data.token);
      await loadMe(data.token);
    }
  };

  const logout = async () => {
    if (auth?.token) {
      try {
        await api("/api/auth/logout", { method: "POST" }, auth.token);
      } catch {
        /* ignore */
      }
    }
    setStoredToken(null);
    setAuth(null);
  };

  const refresh = async () => {
    if (!auth?.token) return;
    await loadMe(auth.token);
  };

  const setSucursal = async (id: number) => {
    if (!auth?.token) return;
    await api("/api/session/sucursal", {
      method: "PUT",
      body: JSON.stringify({ id_sucursal: id }),
    }, auth.token);
    await loadMe(auth.token);
  };

  const setIsla = useCallback(async (id: number) => {
    if (!auth?.token) return;
    await api("/api/session/isla", {
      method: "PUT",
      body: JSON.stringify({ id_isla: id }),
    }, auth.token);
    await loadMe(auth.token);
  }, [auth?.token, loadMe]);

  const value = useMemo(
    () => ({ auth, loading, login, register, logout, refresh, setSucursal, setIsla }),
    [auth, loading, login, register, logout, refresh, setSucursal, setIsla],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside provider");
  return ctx;
}

export function usePermissions(): Permissions {
  return useAuth().auth?.permissions ?? defaultPerms;
}
