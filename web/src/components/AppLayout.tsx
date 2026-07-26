import { useEffect, useMemo, useState, useCallback } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth, usePermissions } from "../context/AuthContext";
import { api } from "../api/client";
import { ModuleLauncher } from "./ModuleLauncher";
import { ProfileMenu } from "./ProfileMenu";
import { ChatOverlay } from "./ChatOverlay";

const ROUTE_LABELS: Record<string, string> = {
  "/": "Inicio",
  "/sucursales": "Sucursales",
  "/islas": "Islas",
  "/clientes": "Clientes",
  "/vehiculos": "Vehículos",
  "/citas": "Citas",
  "/usuarios": "Usuarios",
  "/chat": "Asistente",
};

function ChatHeaderIcon() {
  return (
    <svg className="header-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
    </svg>
  );
}

export function AppLayout() {
  const { auth, logout, setSucursal } = useAuth();
  const perms = usePermissions();
  const navigate = useNavigate();
  const location = useLocation();
  const [sucursales, setSucursales] = useState<Array<{ id: number; nombre: string }>>([]);
  const [chatOpen, setChatOpen] = useState(false);
  const [modulesOpen, setModulesOpen] = useState(false);

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

  useEffect(() => {
    if (!auth || !perms.is_staff || auth.user.id_sucursal || sucursales.length === 0) return;
    setSucursal(sucursales[0].id);
  }, [auth, perms.is_staff, sucursales, setSucursal]);

  const breadcrumb = useMemo(() => {
    if (location.pathname === "/" && perms.needs_taller_setup) {
      return "Inicio / Sucursales";
    }
    const base = ROUTE_LABELS[location.pathname] ?? "IESPRO-Taller";
    return base === "Inicio" ? "Inicio / IESPRO-Taller" : `Inicio / ${base}`;
  }, [location.pathname, perms.needs_taller_setup]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  if (!auth) return null;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-left">
          <button
            type="button"
            className="header-icon-btn"
            onClick={() => setModulesOpen(true)}
            aria-label="Abrir módulos"
            title="Módulos"
          >
            ☰
          </button>
          <span className="header-breadcrumb">{breadcrumb}</span>
        </div>
        <div className="header-toolbar">
          <button
            type="button"
            className="header-icon-btn"
            onClick={() => setChatOpen(true)}
            disabled={!auth.user.id_sucursal}
            title={auth.user.id_sucursal ? "Asistente IA" : "Elige una sucursal"}
            aria-label="Asistente IA"
          >
            <ChatHeaderIcon />
          </button>
          <ProfileMenu onLogout={handleLogout} />
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <span>Derechos reservados 2026 — IESPRO-Taller</span>
        <span>Versión 1.0</span>
      </footer>
      <ModuleLauncher open={modulesOpen} onClose={() => setModulesOpen(false)} />
      <ChatOverlay open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  );
}
