import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { SidePanel } from "../components/SidePanel";

interface Cita {
  id: number;
  cliente?: string;
  placa?: string;
  fecha_cita?: string;
  estado_label?: string;
  mecanico?: string;
  isla?: string;
  descripcion_fallo?: string;
}

interface CatalogItem {
  id: number;
  nombre: string;
}

interface Vehiculo {
  id: number;
  placa?: string;
  marca?: string;
  modelo?: string;
}

export function CitasPage() {
  const { auth } = useAuth();
  const perms = usePermissions();
  const [searchParams] = useSearchParams();
  const [rows, setRows] = useState<Cita[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<{
    cita: Record<string, unknown>;
    falla: Record<string, unknown> | null;
  } | null>(null);
  const [clientes, setClientes] = useState<CatalogItem[]>([]);
  const [vehiculos, setVehiculos] = useState<Vehiculo[]>([]);
  const [mecanicos, setMecanicos] = useState<CatalogItem[]>([]);
  const [islas, setIslas] = useState<CatalogItem[]>([]);
  const [servicios, setServicios] = useState<Array<{ id: number; nombre: string; precio?: number }>>([]);
  const [estados, setEstados] = useState<string[]>([]);
  const [form, setForm] = useState({
    id_cliente: "",
    id_vehiculo: "",
    fecha_cita: new Date().toISOString().slice(0, 10),
    hora_cita: "09:00",
    descripcion_fallo: "",
    fecha_compromiso: new Date().toISOString().slice(0, 10),
    hora_compromiso: "18:00:00",
    id_mecanico: "",
    id_isla: "",
    servicio_ids: [] as number[],
  });
  const [manage, setManage] = useState({
    estado: "",
    diagnostico: "",
    observaciones: "",
    solucion: "",
    id_mecanico: "",
    id_isla: "",
  });
  const [error, setError] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  const load = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ citas: Cita[] }>("/api/citas", {}, auth.token);
    setRows(res.citas);
  }, [auth]);

  const loadFormData = useCallback(async () => {
    if (!auth) return;
    const est = await api<{ items: string[] }>("/api/catalogos/estados-cita", {}, auth.token);
    setEstados(est.items);
    if (!perms.is_cliente) {
      const cl = await api<{ clientes: CatalogItem[] }>("/api/clientes", {}, auth.token);
      setClientes(cl.clientes);
    }
    if (perms.can_manage_branch || perms.is_mecanico) {
      const [m, i, s] = await Promise.all([
        api<{ items: CatalogItem[] }>("/api/catalogos/mecanicos", {}, auth.token),
        auth.user.id_sucursal
          ? api<{ islas: CatalogItem[] }>(`/api/sucursales/${auth.user.id_sucursal}/islas`, {}, auth.token)
          : Promise.resolve({ islas: [] }),
        api<{ items: Array<{ id: number; nombre: string; precio?: number }> }>(
          "/api/catalogos/mantenimiento",
          {},
          auth.token,
        ),
      ]);
      setMecanicos(m.items);
      setIslas(i.islas);
      setServicios(s.items);
    }
  }, [auth, perms]);

  useEffect(() => {
    load();
    loadFormData();
  }, [load, loadFormData]);

  const loadVehiculos = async (idCliente: number) => {
    if (!auth) return;
    const res = await api<{ vehiculos: Vehiculo[] }>(
      `/api/vehiculos?id_cliente=${idCliente}`,
      {},
      auth.token,
    );
    setVehiculos(res.vehiculos);
  };

  useEffect(() => {
    if (perms.is_cliente && auth?.user.id_cliente) {
      loadVehiculos(auth.user.id_cliente);
    }
  }, [auth, perms.is_cliente]);

  const onClienteChange = async (id: string) => {
    setForm((f) => ({ ...f, id_cliente: id }));
    if (id) await loadVehiculos(Number(id));
  };

  const createCita = async () => {
    if (!auth) return;
    setError("");
    try {
      await api("/api/citas", {
        method: "POST",
        body: JSON.stringify({
          id_cliente: form.id_cliente ? Number(form.id_cliente) : null,
          id_vehiculo: Number(form.id_vehiculo),
          fecha_cita: form.fecha_cita,
          hora_cita: form.hora_cita,
          descripcion_fallo: form.descripcion_fallo,
          fecha_compromiso: form.fecha_compromiso,
          hora_compromiso: form.hora_compromiso,
          id_mecanico: form.id_mecanico ? Number(form.id_mecanico) : null,
          id_isla: form.id_isla ? Number(form.id_isla) : null,
          servicio_ids: form.servicio_ids,
        }),
      }, auth.token);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  const openCita = async (id: number) => {
    if (!auth || !perms.can_manage_citas) return;
    setSelected(id);
    const res = await api<{ cita: Record<string, unknown>; falla: Record<string, unknown> | null }>(
      `/api/citas/${id}`,
      {},
      auth.token,
    );
    setDetail(res);
    setManage({
      estado: String(res.cita.estado_label || ""),
      diagnostico: String(res.falla?.diagnostico || ""),
      observaciones: String(res.falla?.observaciones || ""),
      solucion: String(res.falla?.solucion || ""),
      id_mecanico: String(res.cita.id_mecanico || ""),
      id_isla: String(res.cita.id_isla || ""),
    });
    setDrawerOpen(true);
  };

  useEffect(() => {
    const id = searchParams.get("cita");
    if (id && rows.length && perms.can_manage_citas) {
      openCita(Number(id));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams.get("cita"), rows.length]);

  const updateCita = async () => {
    if (!auth || !selected) return;
    setError("");
    try {
      await api(`/api/citas/${selected}`, {
        method: "PATCH",
        body: JSON.stringify({
          estado: manage.estado,
          diagnostico: manage.diagnostico || null,
          observaciones: manage.observaciones || null,
          solucion: manage.solucion || null,
          id_mecanico: manage.id_mecanico ? Number(manage.id_mecanico) : null,
          id_isla: manage.id_isla ? Number(manage.id_isla) : null,
        }),
      }, auth.token);
      setSelected(null);
      setDetail(null);
      setDrawerOpen(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  const title = perms.is_cliente ? "Mis Citas" : "Citas";

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>{title}</h2>
          <p className="muted">Agenda y seguimiento de órdenes</p>
        </div>
        {(perms.can_create_citas || perms.is_cliente) && (
          <button type="button" className="btn" onClick={() => setCreateOpen(true)}>
            {perms.is_cliente ? "+ Solicitar cita" : "+ Crear cita"}
          </button>
        )}
      </div>
      {error && <p className="error-text">{error}</p>}
      <div className="section-card">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                {!perms.is_cliente && <th>Cliente</th>}
                <th>Placa</th>
                <th>Fecha</th>
                <th>Estado</th>
                <th>Mecánico</th>
                <th>Isla</th>
                <th>Falla</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr
                  key={c.id}
                  className={perms.can_manage_citas ? "clickable" : ""}
                  onClick={() => perms.can_manage_citas && openCita(c.id)}
                >
                  {!perms.is_cliente && <td>{c.cliente}</td>}
                  <td>{c.placa}</td>
                  <td>{c.fecha_cita}</td>
                  <td>{c.estado_label}</td>
                  <td>{c.mecanico}</td>
                  <td>{c.isla}</td>
                  <td>{c.descripcion_fallo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <SidePanel
        open={drawerOpen && selected !== null && perms.can_manage_citas}
        title={`Gestionar cita #${selected ?? ""}`}
        onClose={() => { setDrawerOpen(false); setSelected(null); setDetail(null); }}
      >
        {detail && (
          <>
            <p className="muted">Falla: {String(detail.cita.descripcion_fallo || "—")}</p>
            <div className="form-grid">
              <div className="form-row">
                <label>Estado</label>
                <select value={manage.estado} onChange={(e) => setManage({ ...manage, estado: e.target.value })}>
                  {estados.map((e) => <option key={e} value={e}>{e}</option>)}
                </select>
              </div>
              {["diagnostico", "observaciones", "solucion"].map((k) => (
                <div className="form-row" key={k}>
                  <label>{k}</label>
                  <input
                    value={manage[k as keyof typeof manage]}
                    onChange={(e) => setManage({ ...manage, [k]: e.target.value })}
                  />
                </div>
              ))}
              {perms.can_manage_branch && (
                <>
                  <div className="form-row">
                    <label>Mecánico</label>
                    <select
                      value={manage.id_mecanico}
                      onChange={(e) => setManage({ ...manage, id_mecanico: e.target.value })}
                    >
                      {mecanicos.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
                    </select>
                  </div>
                  <div className="form-row">
                    <label>Isla</label>
                    <select value={manage.id_isla} onChange={(e) => setManage({ ...manage, id_isla: e.target.value })}>
                      {islas.map((i) => <option key={i.id} value={i.id}>{i.nombre}</option>)}
                    </select>
                  </div>
                </>
              )}
              <button type="button" className="btn" onClick={updateCita}>Guardar cambios</button>
            </div>
          </>
        )}
      </SidePanel>

      <SidePanel
        open={createOpen}
        title={perms.is_cliente ? "Solicitar cita" : "Nueva cita"}
        onClose={() => setCreateOpen(false)}
      >
        <div className="form-grid">
          {!perms.is_cliente && (
            <div className="form-row">
              <label>Cliente</label>
              <select value={form.id_cliente} onChange={(e) => onClienteChange(e.target.value)}>
                <option value="">Selecciona</option>
                {clientes.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
              </select>
            </div>
          )}
          <div className="form-row">
            <label>Vehículo</label>
            <select value={form.id_vehiculo} onChange={(e) => setForm({ ...form, id_vehiculo: e.target.value })}>
              <option value="">Selecciona</option>
              {vehiculos.map((v) => (
                <option key={v.id} value={v.id}>{v.placa} — {v.marca} {v.modelo}</option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Fecha cita</label>
            <input type="date" value={form.fecha_cita} onChange={(e) => setForm({ ...form, fecha_cita: e.target.value })} />
          </div>
          <div className="form-row">
            <label>Hora cita</label>
            <input value={form.hora_cita} onChange={(e) => setForm({ ...form, hora_cita: e.target.value })} />
          </div>
          <div className="form-row">
            <label>Descripción fallo</label>
            <input value={form.descripcion_fallo} onChange={(e) => setForm({ ...form, descripcion_fallo: e.target.value })} />
          </div>
          {perms.can_manage_branch && (
            <>
              <div className="form-row">
                <label>Mecánico</label>
                <select value={form.id_mecanico} onChange={(e) => setForm({ ...form, id_mecanico: e.target.value })}>
                  {mecanicos.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
                </select>
              </div>
              <div className="form-row">
                <label>Isla</label>
                <select value={form.id_isla} onChange={(e) => setForm({ ...form, id_isla: e.target.value })}>
                  {islas.map((i) => <option key={i.id} value={i.id}>{i.nombre}</option>)}
                </select>
              </div>
            </>
          )}
          <div className="form-row">
            <label>Fecha compromiso</label>
            <input type="date" value={form.fecha_compromiso} onChange={(e) => setForm({ ...form, fecha_compromiso: e.target.value })} />
          </div>
          <div className="form-row">
            <label>Hora compromiso</label>
            <input value={form.hora_compromiso} onChange={(e) => setForm({ ...form, hora_compromiso: e.target.value })} />
          </div>
          <div className="form-row">
            <label>Mantenimiento</label>
            <select
              multiple
              value={form.servicio_ids.map(String)}
              onChange={(e) => {
                const ids = Array.from(e.target.selectedOptions).map((o) => Number(o.value));
                setForm({ ...form, servicio_ids: ids });
              }}
              className="multi-select"
            >
              {servicios.map((s) => (
                <option key={s.id} value={s.id}>{s.nombre} — ${s.precio}</option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className="btn"
            onClick={async () => {
              await createCita();
              setCreateOpen(false);
            }}
          >
            {perms.is_cliente ? "Solicitar cita" : "Crear cita"}
          </button>
        </div>
      </SidePanel>
    </div>
  );
}
