import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";

interface Vehiculo {
  id: number;
  placa?: string;
  marca?: string;
  modelo?: string;
  cliente?: string;
  mecanico_asignado?: string;
  numero_economico?: string;
  kilometraje?: number;
}

interface CatalogItem {
  id: number;
  nombre: string;
}

interface Cliente {
  id: number;
  nombre: string;
}

export function VehiculosPage() {
  const { auth } = useAuth();
  const perms = usePermissions();
  const [rows, setRows] = useState<Vehiculo[]>([]);
  const [marcas, setMarcas] = useState<CatalogItem[]>([]);
  const [combustibles, setCombustibles] = useState<CatalogItem[]>([]);
  const [unidades, setUnidades] = useState<CatalogItem[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [mecanicos, setMecanicos] = useState<CatalogItem[]>([]);
  const [form, setForm] = useState({
    numero_economico: "",
    placa: "",
    serie: "",
    modelo: "",
    kilometraje: "0",
    dias_mantenimiento: "90",
    observaciones: "",
    id_cliente: "",
    id_mecanico_asignado: "",
    id_marca: "",
    id_tipo_combustible: "",
    id_tipo_unidad: "",
  });
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ vehiculos: Vehiculo[] }>("/api/vehiculos", {}, auth.token);
    setRows(res.vehiculos);
  }, [auth]);

  const loadCatalogs = useCallback(async () => {
    if (!auth) return;
    const [m, c, u, cl, mec] = await Promise.all([
      api<{ items: CatalogItem[] }>("/api/catalogos/marcas", {}, auth.token),
      api<{ items: CatalogItem[] }>("/api/catalogos/combustibles", {}, auth.token),
      api<{ items: CatalogItem[] }>("/api/catalogos/unidades", {}, auth.token),
      api<{ clientes: Cliente[] }>("/api/clientes", {}, auth.token),
      perms.can_manage_branch
        ? api<{ items: CatalogItem[] }>("/api/catalogos/mecanicos", {}, auth.token)
        : Promise.resolve({ items: [] }),
    ]);
    setMarcas(m.items);
    setCombustibles(c.items);
    setUnidades(u.items);
    setClientes(cl.clientes);
    setMecanicos(mec.items);
    if (m.items.length) setForm((f) => ({ ...f, id_marca: String(m.items[0].id) }));
    if (c.items.length) setForm((f) => ({ ...f, id_tipo_combustible: String(c.items[0].id) }));
    if (u.items.length) setForm((f) => ({ ...f, id_tipo_unidad: String(u.items[0].id) }));
  }, [auth, perms.can_manage_branch]);

  useEffect(() => {
    load();
    loadCatalogs();
  }, [load, loadCatalogs]);

  const save = async () => {
    if (!auth) return;
    setError("");
    try {
      await api("/api/vehiculos", {
        method: "POST",
        body: JSON.stringify({
          numero_economico: form.numero_economico,
          placa: form.placa,
          serie: form.serie,
          modelo: form.modelo,
          kilometraje: Number(form.kilometraje),
          dias_mantenimiento: Number(form.dias_mantenimiento),
          observaciones: form.observaciones || null,
          id_cliente: perms.is_cliente ? null : Number(form.id_cliente),
          id_mecanico_asignado: form.id_mecanico_asignado ? Number(form.id_mecanico_asignado) : null,
          id_marca: Number(form.id_marca),
          id_tipo_combustible: Number(form.id_tipo_combustible),
          id_tipo_unidad: Number(form.id_tipo_unidad),
        }),
      }, auth.token);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  const title = perms.is_cliente ? "Mis Vehículos" : "Vehículos";

  return (
    <div className="page">
      <div className="page-header"><h2>{title}</h2></div>
      {error && <p className="error-text">{error}</p>}
      <div className="split-layout">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Placa</th>
                <th>Marca</th>
                <th>Modelo</th>
                <th>Cliente</th>
                {!perms.is_cliente && <th>Mecánico</th>}
                <th>No. econ.</th>
                <th>Km</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((v) => (
                <tr key={v.id}>
                  <td>{v.placa}</td>
                  <td>{v.marca}</td>
                  <td>{v.modelo}</td>
                  <td>{v.cliente}</td>
                  {!perms.is_cliente && <td>{v.mecanico_asignado}</td>}
                  <td>{v.numero_economico}</td>
                  <td>{v.kilometraje}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="side-panel">
          <h3>{perms.is_cliente ? "Registrar mi vehículo" : "Nuevo vehículo"}</h3>
          <div className="form-grid">
            {["numero_economico", "placa", "serie", "modelo", "kilometraje", "dias_mantenimiento"].map((key) => (
              <div className="form-row" key={key}>
                <label>{key.replace(/_/g, " ")}</label>
                <input
                  value={form[key as keyof typeof form]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                />
              </div>
            ))}
            <div className="form-row">
              <label>Observaciones</label>
              <input value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} />
            </div>
            {!perms.is_cliente && (
              <div className="form-row">
                <label>Propietario</label>
                <select value={form.id_cliente} onChange={(e) => setForm({ ...form, id_cliente: e.target.value })}>
                  <option value="">Selecciona</option>
                  {clientes.map((c) => (
                    <option key={c.id} value={c.id}>{c.nombre}</option>
                  ))}
                </select>
              </div>
            )}
            {perms.can_manage_branch && (
              <div className="form-row">
                <label>Mecánico</label>
                <select
                  value={form.id_mecanico_asignado}
                  onChange={(e) => setForm({ ...form, id_mecanico_asignado: e.target.value })}
                >
                  <option value="">— Sin asignar —</option>
                  {mecanicos.map((m) => (
                    <option key={m.id} value={m.id}>{m.nombre}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="form-row">
              <label>Marca</label>
              <select value={form.id_marca} onChange={(e) => setForm({ ...form, id_marca: e.target.value })}>
                {marcas.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
              </select>
            </div>
            <div className="form-row">
              <label>Combustible</label>
              <select
                value={form.id_tipo_combustible}
                onChange={(e) => setForm({ ...form, id_tipo_combustible: e.target.value })}
              >
                {combustibles.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
              </select>
            </div>
            <div className="form-row">
              <label>Tipo unidad</label>
              <select value={form.id_tipo_unidad} onChange={(e) => setForm({ ...form, id_tipo_unidad: e.target.value })}>
                {unidades.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
              </select>
            </div>
            <button className="btn" onClick={save}>Guardar vehículo</button>
          </div>
        </div>
      </div>
    </div>
  );
}
