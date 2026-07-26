import { useEffect, useMemo, useState, useCallback } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth, usePermissions } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { api } from "../api/client";
import { ModuleLauncher } from "./ModuleLauncher";
import { ProfileMenu } from "./ProfileMenu";
import { ChatOverlay } from "./ChatOverlay";

const ROUTE_LABELS: Record<string, string> = {
  "/": "Inicio",
  "/clientes": "Clientes",
  "/vehiculos": "Vehículos",
  "/citas": "Órdenes",
  "/ordenes": "Órdenes",
  "/inventario": "Inventario",
  "/sucursales": "Taller",
  "/chat": "Asistente",
};

function ChatHeaderIcon() {
  return (
    <svg className="header-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z" />
    </svg>
  );
}

function ThemeToggleIcon({ isDark }: { isDark: boolean }) {
  if (isDark) {
    return (
      <svg className="header-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
      </svg>
    );
  }
  return (
    <svg className="header-svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

export function AppLayout() {
  const { auth, logout, setIsla, refresh } = useAuth();
  const perms = usePermissions();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [islas, setIslas] = useState<Array<{ id: number; nombre: string }>>([]);
  const [chatOpen, setChatOpen] = useState(false);
  const [modulesOpen, setModulesOpen] = useState(false);

  const loadIslas = useCallback(async () => {
    if (!auth || !perms.is_staff) return;
    try {
      const res = await api<{ islas: Array<{ id: number; nombre: string }>; id_isla_activa?: number }>(
        "/api/islas",
        {},
        auth.token,
      );
      setIslas(res.islas);
      if (!auth.user.id_isla && res.islas[0]) {
        await setIsla(res.islas[0].id);
      }
    } catch {
      setIslas([]);
    }
  }, [auth, perms.is_staff, setIsla]);

  useEffect(() => {
    loadIslas();
  }, [loadIslas]);

  useEffect(() => {
    if (!auth || !perms.is_staff || auth.user.id_sucursal) return;
    refresh();
  }, [auth, perms.is_staff, refresh]);

  const breadcrumb = useMemo(() => {
    const base = ROUTE_LABELS[location.pathname] ?? "IESPRO-Taller";
    return base === "Inicio" ? "Inicio / IESPRO-Taller" : `Inicio / ${base}`;
  }, [location.pathname]);

  const activeIsla = islas.find((i) => i.id === auth.user.id_isla);
  const chatReady = Boolean(auth.user.id_sucursal && (perms.is_cliente || auth.user.id_isla));

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
          {perms.is_staff && islas.length > 0 && (
            <div className="header-isla-picker">
              <select
                id="header-isla-select"
                className="header-isla-select"
                value={auth.user.id_isla ?? ""}
                onChange={(e) => void setIsla(Number(e.target.value))}
                title="Bahía de trabajo activa"
                aria-label="Isla activa"
              >
                {islas.map((i) => (
                  <option key={i.id} value={i.id}>{i.nombre}</option>
                ))}
              </select>
              <span className="profile-chevron" aria-hidden>▾</span>
            </div>
          )}
        </div>

        <div className="header-toolbar">
          <button
            type="button"
            className="header-icon-btn"
            onClick={toggleTheme}
            title={isDark ? "Modo claro" : "Modo oscuro"}
            aria-label={isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
          >
            <ThemeToggleIcon isDark={isDark} />
          </button>
          <button
            type="button"
            className="header-icon-btn"
            onClick={() => setChatOpen(true)}
            disabled={!chatReady}
            title={
              chatReady
                ? `Asistente IA${activeIsla ? ` — ${activeIsla.nombre}` : ""}`
                : "Selecciona una isla para usar el asistente"
            }
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
