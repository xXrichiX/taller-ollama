import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { AppLoader } from "../components/AppLoader";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { estadoPillClass } from "../utils/ordenStatus";

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
  ordenes: CitaRow[];
  citas_lista?: CitaRow[];
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

function DashMetricCard({
  label,
  value,
  icon,
  variant = "default",
  footer,
  onClick,
}: {
  label: string;
  value: number;
  icon: ReactNode;
  variant?: "default" | "warn" | "process" | "done";
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

function IconCalendar() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
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
  }, [auth, auth?.user.id_isla]);

  useEffect(() => {
    load();
    const interval = window.setInterval(() => load(true), 15000);
    return () => window.clearInterval(interval);
  }, [load]);

  const openCita = (id: number) => {
    if (perms.can_manage_citas) navigate(`/citas?cita=${id}`);
    else navigate("/citas");
  };

  const goCitas = () => navigate("/citas");

  if (!data) {
    if (loading) {
      return <AppLoader fullScreen={false} />;
    }
    return null;
  }

  const s = data.stats;
  const showCliente = !perms.is_cliente;
  const isStaff = perms.can_manage_branch && !perms.is_cliente;
  const citas = data.citas_lista ?? data.ordenes ?? [];

  return (
    <div className="page page-dashboard">
      <header className="dash-header">
        <h1>{data.title}</h1>
      </header>

      {isStaff && (
        <div className="dash-cards-row dash-cards-row--2">
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
        </div>
      )}

      {perms.is_cliente && (
        <div className="dash-cards-row dash-cards-row--1">
          <DashMetricCard
            label="Mis vehículos"
            value={s.vehiculos ?? 0}
            icon={<IconCar />}
            footer={<DashSparkline />}
            onClick={() => navigate("/vehiculos")}
          />
        </div>
      )}

      <div className="dash-section-head">
        <h2>Citas</h2>
      </div>

      <div className="dash-cards-row dash-cards-row--3">
        <DashMetricCard
          label="Total"
          value={s.citas ?? 0}
          icon={<IconCalendar />}
          variant="warn"
          footer={<DashSparkline color="#f59e0b" />}
          onClick={goCitas}
        />
        <DashMetricCard
          label="En proceso"
          value={s.en_proceso ?? 0}
          icon={<IconCar />}
          variant="process"
          onClick={goCitas}
        />
        <DashMetricCard
          label="Completadas"
          value={s.completadas ?? 0}
          icon={<IconCheck />}
          variant="done"
          onClick={goCitas}
        />
      </div>

      <section className="dash-table-panel section-card dash-ordenes-panel">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Hora</th>
                {showCliente && <th>Cliente</th>}
                <th>Vehículo</th>
                <th>Falla / servicio</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {citas.length === 0 ? (
                <tr>
                  <td colSpan={showCliente ? 6 : 5} className="table-no-results">
                    Sin citas en esta isla
                  </td>
                </tr>
              ) : (
                citas.map((o) => (
                  <tr
                    key={o.id}
                    className={perms.can_manage_citas ? "clickable" : ""}
                    onClick={() => openCita(o.id)}
                  >
                    <td>{o.fecha_programada || "—"}</td>
                    <td>{o.hora || "—"}</td>
                    {showCliente && <td>{o.cliente || "—"}</td>}
                    <td>{o.vehiculo || "—"}</td>
                    <td className="truncate">{o.servicio || "—"}</td>
                    <td>
                      <span className={estadoPillClass(o.estado)}>{o.estado || "—"}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
