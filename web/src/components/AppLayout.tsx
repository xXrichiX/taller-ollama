import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth, usePermissions } from "../context/AuthContext";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { ProfileMenu } from "./ProfileMenu";
import { ChatOverlay } from "./ChatOverlay";

export function AppLayout() {
  const { auth, logout, setSucursal } = useAuth();
  const perms = usePermissions();
  const navigate = useNavigate();
  const [sucursales, setSucursales] = useState<Array<{ id: number; nombre: string }>>([]);
  const [chatOpen, setChatOpen] = useState(false);

  const loadSucursales = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ sucursales: Array<{ id: number; nombre: string }> }>(
      "/api/sucursales",
      {},
      auth.token,
    );
    setSucursales(res.sucursales);
  }, [auth]);

  useEffect(() => {
    if (perms.is_staff) loadSucursales();
  }, [loadSucursales, perms.is_staff]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  if (!auth) return null;

  const tabs: Array<{ path: string; label: string; show: boolean }> = [
    { path: "/", label: "Inicio", show: true },
    { path: "/sucursales", label: "Sucursales", show: perms.is_staff },
    { path: "/clientes", label: "Clientes", show: perms.is_staff },
    { path: "/vehiculos", label: perms.is_cliente ? "Mis Vehículos" : "Vehículos", show: true },
    { path: "/citas", label: perms.is_cliente ? "Mis Citas" : "Citas", show: true },
    { path: "/usuarios", label: "Usuarios", show: perms.can_manage_usuarios },
  ];

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-left">
          <div className="brand">
            <span className="brand-mark">IE</span>
            <div>
              <h1>IESPRO-Taller</h1>
              <span className="brand-sub">Gestión inteligente</span>
            </div>
          </div>
          <ProfileMenu onLogout={handleLogout} />
          {perms.is_staff && sucursales.length > 0 && (
            <select
              className="sucursal-select"
              value={auth.user.id_sucursal ?? ""}
              onChange={(e) => setSucursal(Number(e.target.value))}
            >
              <option value="" disabled>Sucursal activa</option>
              {sucursales.map((s) => (
                <option key={s.id} value={s.id}>{s.nombre}</option>
              ))}
            </select>
          )}
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="btn btn-accent"
            onClick={() => setChatOpen(true)}
            disabled={!auth.user.id_sucursal}
          >
            Abrir asistente
          </button>
        </div>
      </header>
      <nav className="nav-tabs">
        {tabs.filter((t) => t.show).map((t) => (
          <NavLink
            key={t.path}
            to={t.path}
            end={t.path === "/"}
            className={({ isActive }) => `nav-tab ${isActive ? "active" : ""}`}
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
      <main className="app-main">
        <Outlet />
      </main>
      <ChatOverlay open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  );
}
