import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";

interface CitaRow {
  id: number;
  hora?: string;
  fecha_programada?: string;
  cliente?: string;
  vehiculo?: string;
  estado?: string;
  mecanico?: string;
  servicio?: string;
}

interface DashboardData {
  title: string;
  stats: Record<string, number>;
  islas_ocupadas: number;
  islas_total: number;
  mecanicos_ocupados: number;
  mecanicos_total: number;
  recent_citas: CitaRow[];
  pending_citas: CitaRow[];
}

function DashSparkline({ color = "#2185d0" }: { color?: string }) {
  return (
    <svg className="dash-sparkline" viewBox="0 0 80 24" preserveAspectRatio="none" aria-hidden>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points="0,18 12,14 24,16 36,10 48,12 60,6 72,8 80,4"
      />
    </svg>
  );
}

function DashProgress({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="dash-progress">
      <div className="dash-progress-meta">
        <span>{label}</span>
        <span>{value}/{max}</span>
      </div>
      <div className="dash-progress-track">
        <div className="dash-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="dash-progress-pct">{pct}% ocupado</span>
    </div>
  );
}

function DashMetricCard({
  label,
  value,
  icon,
  variant = "default",
  subtitle,
  footer,
  onClick,
}: {
  label: string;
  value: number;
  icon: ReactNode;
  variant?: "default" | "warn" | "pending" | "process" | "done";
  subtitle?: string;
  footer?: ReactNode;
  onClick?: () => void;
}) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      className={`dash-card dash-card--${variant}`}
      onClick={onClick}
    >
      <div className="dash-card-top">
        <div className="dash-card-icon">{icon}</div>
        <div className="dash-card-body">
          <span className="dash-card-label">{label}</span>
          <span className="dash-card-value">{value.toLocaleString("es-MX")}</span>
          {subtitle && <span className="dash-card-sub">{subtitle}</span>}
        </div>
      </div>
      {footer && <div className="dash-card-footer">{footer}</div>}
    </Tag>
  );
}

function IconUsers() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function IconCar() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M5 17h14M5 17l-1-5 2-4h12l2 4-1 5M5 17H3M19 17h2" />
      <circle cx="7.5" cy="17" r="1.5" />
      <circle cx="16.5" cy="17" r="1.5" />
    </svg>
  );
}

function IconIsland() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M12 3c-3 4-8 5-8 11a8 8 0 0 0 16 0c0-6-5-7-8-11z" />
      <path d="M8 20c2-1 6-1 8 0" />
    </svg>
  );
}

function IconWrench() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function IconCalendar() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  );
}

function IconAlert() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <path d="M12 9v4M12 17h.01" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <path d="M22 4 12 14.01l-3-3" />
    </svg>
  );
}

function MiniCitasTable({
  rows,
  showCliente,
  onRowClick,
}: {
  rows: CitaRow[];
  showCliente: boolean;
  onRowClick?: (id: number) => void;
}) {
  return (
    <div className="dash-mini-table-wrap">
      <table className="dash-mini-table">
        <thead>
          <tr>
            <th>Hora</th>
            {showCliente && <th>Cliente</th>}
            <th>Vehículo</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={showCliente ? 4 : 3} className="dash-mini-empty">Sin datos</td>
            </tr>
          ) : (
            rows.slice(0, 4).map((c) => (
              <tr
                key={c.id}
                className={onRowClick ? "clickable" : undefined}
                onClick={() => onRowClick?.(c.id)}
              >
                <td>{c.hora || "—"}</td>
                {showCliente && <td>{c.cliente || "—"}</td>}
                <td>{c.vehiculo || "—"}</td>
                <td><span className="status-pill status-pill-sm">{c.estado}</span></td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function DashboardPage() {
  const { auth } = useAuth();
  const perms = usePermissions();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (silent = false) => {
    if (!auth) return;
    const res = await api<DashboardData>("/api/dashboard", {}, auth.token);
    setData(res);
    if (!silent) setLoading(false);
  }, [auth]);

  useEffect(() => {
    load();
    const interval = window.setInterval(() => load(true), 15000);
    return () => window.clearInterval(interval);
  }, [load]);

  const openCita = (id: number) => {
    if (perms.can_manage_citas) navigate(`/citas?cita=${id}`);
    else navigate("/citas");
  };

  if (!data) {
    if (loading) {
      return (
        <div className="page page-dashboard">
          <div className="loading-state">Cargando panel…</div>
        </div>
      );
    }
    return null;
  }

  const s = data.stats;
  const showCliente = !perms.is_cliente;
  const isStaff = perms.can_manage_branch && !perms.is_cliente;
  const mecanicosLibres = Math.max(data.mecanicos_total - data.mecanicos_ocupados, 0);
  const mecanicosDispPct = data.mecanicos_total > 0
    ? Math.round((mecanicosLibres / data.mecanicos_total) * 100)
    : 0;

  return (
    <div className="page page-dashboard">
      <header className="dash-header">
        <h1>{data.title}</h1>
      </header>

      {isStaff && (
        <div className="dash-cards-row">
          <DashMetricCard
            label="Clientes"
            value={s.clientes ?? 0}
            icon={<IconUsers />}
            footer={<DashSparkline />}
            onClick={() => navigate("/clientes")}
          />
          <DashMetricCard
            label="Vehículos"
            value={s.vehiculos ?? 0}
            icon={<IconCar />}
            footer={<DashSparkline color="#38bdf8" />}
            onClick={() => navigate("/vehiculos")}
          />
          <DashMetricCard
            label="Islas"
            value={s.islas ?? 0}
            icon={<IconIsland />}
            footer={(
              <DashProgress
                value={data.islas_ocupadas}
                max={data.islas_total || 1}
                label="Ocupación"
              />
            )}
            onClick={() => navigate("/sucursales")}
          />
          <DashMetricCard
            label="Mecánicos"
            value={s.mecanicos ?? 0}
            icon={<IconWrench />}
            footer={(
              <div className="dash-progress">
                <div className="dash-progress-meta">
                  <span>Disponibilidad</span>
                  <span>{mecanicosLibres}/{data.mecanicos_total}</span>
                </div>
                <div className="dash-progress-track dash-progress-track--green">
                  <div className="dash-progress-fill dash-progress-fill--green" style={{ width: `${mecanicosDispPct}%` }} />
                </div>
              </div>
            )}
            onClick={() => navigate("/usuarios")}
          />
          <DashMetricCard
            label="Citas"
            value={s.citas ?? 0}
            icon={<IconAlert />}
            variant="warn"
            footer={<DashSparkline color="#f59e0b" />}
            onClick={() => navigate("/citas")}
          />
        </div>
      )}

      {!isStaff && (
        <div className={`dash-cards-row${perms.is_cliente ? " dash-cards-row--2" : ""}`}>
          {perms.is_cliente && (
            <DashMetricCard
              label="Vehículos"
              value={s.vehiculos ?? 0}
              icon={<IconCar />}
              footer={<DashSparkline />}
              onClick={() => navigate("/vehiculos")}
            />
          )}
          <DashMetricCard
            label="Citas"
            value={s.citas ?? 0}
            icon={<IconAlert />}
            variant="warn"
            footer={<DashSparkline color="#f59e0b" />}
            onClick={() => navigate("/citas")}
          />
        </div>
      )}

      <div className="dash-cards-row">
        {isStaff && (
          <DashMetricCard
            label="Citas"
            value={s.citas ?? 0}
            icon={<IconCalendar />}
            onClick={() => navigate("/citas")}
          />
        )}
        <DashMetricCard
          label="Pendientes"
          value={s.pendientes ?? 0}
          icon={<IconAlert />}
          variant="pending"
          subtitle="Por iniciar"
          onClick={() => navigate("/citas")}
        />
        <DashMetricCard
          label="En proceso"
          value={s.en_proceso ?? 0}
          icon={<IconCar />}
          variant="process"
          subtitle="Trabajando ahora"
          onClick={() => navigate("/citas")}
        />
        <DashMetricCard
          label="Completadas"
          value={s.completadas ?? 0}
          icon={<IconCheck />}
          variant="done"
          subtitle="Listas para entrega"
          onClick={() => navigate("/citas")}
        />
        <div className="dash-card dash-card--mini-table">
          <div className="dash-card-mini-head">
            <span className="dash-card-label">Citas recientes</span>
          </div>
          <MiniCitasTable
            rows={data.recent_citas}
            showCliente={showCliente}
            onRowClick={perms.can_manage_citas ? openCita : undefined}
          />
        </div>
      </div>

      <div className="dash-tables-block section-card">
        <div className="dash-table-bar">
          <h3>Citas recientes</h3>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Hora</th>
                {showCliente && <th>Cliente</th>}
                <th>Vehículo</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_citas.map((c) => (
                <tr
                  key={c.id}
                  className={perms.can_manage_citas ? "clickable" : ""}
                  onClick={() => openCita(c.id)}
                >
                  <td>{c.hora || "—"}</td>
                  {showCliente && <td>{c.cliente || "—"}</td>}
                  <td>{c.vehiculo || "—"}</td>
                  <td><span className="status-pill">{c.estado}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="dash-table-bar dash-table-bar--split">
          <h3>Citas por iniciar</h3>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Fecha programada</th>
                {showCliente && <th>Cliente</th>}
                <th>Servicio</th>
                <th>Técnico asignado</th>
              </tr>
            </thead>
            <tbody>
              {data.pending_citas.map((c) => (
                <tr
                  key={c.id}
                  className={perms.can_manage_citas ? "clickable" : ""}
                  onClick={() => openCita(c.id)}
                >
                  <td>{c.fecha_programada || "—"}</td>
                  {showCliente && <td>{c.cliente || "—"}</td>}
                  <td className="truncate">{c.servicio || "—"}</td>
                  <td>{c.mecanico || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
