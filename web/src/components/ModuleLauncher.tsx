import { useNavigate } from "react-router-dom";
import { usePermissions } from "../context/AuthContext";

interface Module {
  path: string;
  label: string;
  icon: string;
  show: boolean;
}

export function ModuleLauncher({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const perms = usePermissions();

  const modules: Module[] = [
    { path: "/", label: "Inicio", icon: "⌂", show: true },
    { path: "/sucursales", label: "Sucursales", icon: "▦", show: perms.is_staff },
    { path: "/clientes", label: "Clientes", icon: "👥", show: perms.is_staff },
    { path: "/vehiculos", label: perms.is_cliente ? "Mis Vehículos" : "Vehículos", icon: "🚗", show: true },
    { path: "/citas", label: perms.is_cliente ? "Mis Citas" : "Citas", icon: "📅", show: true },
    { path: "/usuarios", label: "Usuarios", icon: "🔧", show: perms.can_manage_usuarios },
  ];

  if (!open) return null;

  return (
    <>
      <div className="module-backdrop" onClick={onClose} aria-hidden />
      <div className="module-launcher" role="dialog" aria-label="Módulos">
        <div className="module-grid">
          {modules.filter((m) => m.show).map((m) => (
            <button
              key={m.path}
              type="button"
              className="module-tile"
              onClick={() => {
                navigate(m.path);
                onClose();
              }}
            >
              <span className="module-tile-icon" aria-hidden>{m.icon}</span>
              <span className="module-tile-label">{m.label}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
