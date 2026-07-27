import { useNavigate } from "react-router-dom";
import { usePermissions } from "../context/AuthContext";

type ModuleIconName = "home" | "users" | "car" | "orders" | "inventory" | "services" | "workshop";

interface Module {
  path: string;
  label: string;
  icon: ModuleIconName;
  show: boolean;
}

function ModuleIcon({ name }: { name: ModuleIconName }) {
  const svgProps = {
    className: "module-svg-icon",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "home":
      return (
        <svg {...svgProps}>
          <path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-8.5z" />
        </svg>
      );
    case "users":
      return (
        <svg {...svgProps}>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "car":
      return (
        <svg {...svgProps}>
          <path d="M5 17h14M5 17a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm14 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0z" />
          <path d="M3 13l2-6h14l2 6M7 13h10" />
        </svg>
      );
    case "orders":
      return (
        <svg {...svgProps}>
          <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
          <rect x="9" y="3" width="6" height="4" rx="1" />
          <path d="M9 12h6M9 16h6" />
        </svg>
      );
    case "inventory":
      return (
        <svg {...svgProps}>
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
          <path d="M3.3 7.3 12 12l8.7-4.7M12 22V12" />
        </svg>
      );
    case "services":
      return (
        <svg {...svgProps}>
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
        </svg>
      );
    case "workshop":
      return (
        <svg {...svgProps}>
          <path d="M3 21h18M5 21V7l7-4 7 4v14" />
          <path d="M9 21v-6h6v6M9 9h.01M15 9h.01M9 13h.01M15 13h.01" />
        </svg>
      );
    default:
      return null;
  }
}

export function ModuleLauncher({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const perms = usePermissions();

  const modules: Module[] = [
    { path: "/", label: "Inicio", icon: "home", show: true },
    { path: "/clientes", label: "Clientes", icon: "users", show: perms.is_staff },
    { path: "/vehiculos", label: perms.is_cliente ? "Mis Vehículos" : "Vehículos", icon: "car", show: true },
    { path: "/citas", label: perms.is_cliente ? "Mis citas" : "Citas", icon: "orders", show: true },
    { path: "/inventario", label: "Inventario", icon: "inventory", show: perms.is_staff },
    { path: "/servicios", label: "Servicios", icon: "services", show: perms.is_staff },
    { path: "/sucursales", label: "Bahías", icon: "workshop", show: perms.is_staff && perms.show_taller_module },
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
              <span className="module-tile-icon">
                <ModuleIcon name={m.icon} />
              </span>
              <span className="module-tile-label">{m.label}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
