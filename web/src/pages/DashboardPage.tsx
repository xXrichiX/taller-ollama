import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";

interface DashboardData {
  title: string;
  stats: Record<string, number>;
  recent_citas: Array<{
    id: number;
    cliente?: string;
    placa?: string;
    estado?: string;
    mecanico?: string;
    isla?: string;
    descripcion_fallo?: string;
  }>;
}

const STAT_ORDER = [
  "clientes",
  "vehiculos",
  "citas",
  "pendientes",
  "en_proceso",
  "completadas",
  "islas",
  "mecanicos",
] as const;

const STAT_LABELS: Record<string, string> = {
  clientes: "Clientes",
  vehiculos: "Vehículos",
  citas: "Citas",
  pendientes: "Pendientes",
  en_proceso: "En proceso",
  completadas: "Completadas",
  islas: "Islas",
  mecanicos: "Mecánicos",
};

const MODULE_LINKS: Record<string, string> = {
  clientes: "/clientes",
  vehiculos: "/vehiculos",
  citas: "/citas",
  islas: "/sucursales",
  mecanicos: "/usuarios",
};

export function DashboardPage() {
  const { auth } = useAuth();
  const perms = usePermissions();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);

  const load = useCallback(async () => {
    if (!auth) return;
    const res = await api<DashboardData>("/api/dashboard", {}, auth.token);
    setData(res);
  }, [auth]);

  useEffect(() => {
    load();
  }, [load]);

  if (!data) {
    return (
      <div className="page">
        <div className="loading-state">Cargando panel…</div>
      </div>
    );
  }

  const needsSucursal = auth?.permissions.is_staff && !auth.user.id_sucursal;

  const statEntries = STAT_ORDER.filter((key) => key in data.stats).map((key) => ({
    key,
    value: data.stats[key],
    label: STAT_LABELS[key] ?? key,
    link: MODULE_LINKS[key],
  }));

  return (
    <div className="page page-dashboard">
      {needsSucursal && (
        <div className="alert warn">Selecciona una sucursal en el encabezado para ver datos.</div>
      )}
      <div className="dash-layout">
        <div className="dash-panel">
          <div className="dash-panel-head">
            <h2>Resumen del taller</h2>
            <button type="button" className="btn-text" onClick={load}>Actualizar</button>
          </div>
          <ul className="dash-stat-list">
            {statEntries.map(({ key, value, label, link }) => (
              <li key={key}>
                <button
                  type="button"
                  className="dash-stat-row"
                  onClick={() => link && navigate(link)}
                  disabled={!link}
                >
                  <span className="dash-stat-label">{label}</span>
                  <span className="dash-stat-value">{value.toLocaleString("es-MX")}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="section-card dash-table-panel">
          <h3>Citas recientes</h3>
          <div className="table-wrap">
            {data.recent_citas.length === 0 ? (
              <div className="table-empty table-empty-compact">
                <strong>Sin citas recientes</strong>
                Las órdenes nuevas aparecerán aquí.
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Placa</th>
                    <th>Estado</th>
                    <th>Mecánico</th>
                    <th>Isla</th>
                    <th>Falla</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_citas.map((c) => (
                    <tr
                      key={c.id}
                      className={perms.can_manage_citas ? "clickable" : ""}
                      onClick={() => perms.can_manage_citas && navigate(`/citas?cita=${c.id}`)}
                    >
                      <td>{c.cliente}</td>
                      <td><span className="badge">{c.placa}</span></td>
                      <td><span className="status-pill">{c.estado}</span></td>
                      <td>{c.mecanico || "—"}</td>
                      <td>{c.isla || "—"}</td>
                      <td className="truncate">{c.descripcion_fallo}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
