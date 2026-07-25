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

const STAT_ACCENTS = ["blue", "violet", "amber", "emerald", "rose", "cyan", "indigo"];

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

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>{data.title}</h2>
          <p className="muted">Resumen en tiempo real del taller</p>
        </div>
        <button type="button" className="btn-ghost" onClick={load}>Actualizar</button>
      </div>
      {needsSucursal && (
        <div className="alert warn">Selecciona una sucursal en el encabezado para ver datos.</div>
      )}
      <div className="stats-grid">
        {Object.entries(data.stats).map(([key, val], i) => (
          <div key={key} className={`stat-card accent-${STAT_ACCENTS[i % STAT_ACCENTS.length]}`}>
            <div className="label">{labelStat(key)}</div>
            <div className="value">{val}</div>
          </div>
        ))}
      </div>
      <div className="section-card">
        <h3>Citas recientes</h3>
        <div className="table-wrap">
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
                  <td>{c.mecanico}</td>
                  <td>{c.isla}</td>
                  <td className="truncate">{c.descripcion_fallo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function labelStat(key: string): string {
  const map: Record<string, string> = {
    vehiculos: "Vehículos",
    citas: "Citas",
    pendientes: "Pendientes",
    en_proceso: "En proceso",
    completadas: "Completadas",
    clientes: "Clientes",
    islas: "Islas",
    mecanicos: "Mecánicos",
  };
  return map[key] ?? key;
}
