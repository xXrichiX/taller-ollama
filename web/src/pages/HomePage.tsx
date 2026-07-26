import { usePermissions } from "../context/AuthContext";
import { DashboardPage } from "./DashboardPage";
import { SucursalesPage } from "./SucursalesPage";

/** Inicio: sucursales/islas hasta tener taller; después el panel resumen. */
export function HomePage() {
  const perms = usePermissions();
  if (perms.needs_taller_setup) return <SucursalesPage />;
  return <DashboardPage />;
}
