import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { CarEmptyIcon, EmptyState } from "../components/EmptyState";
import { ListToolbar } from "../components/ListToolbar";
import { SidePanel } from "../components/SidePanel";

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

function emptyForm(marca = "", combustible = "", unidad = "") {
  return {
    numero_economico: "",
    placa: "",
    serie: "",
    modelo: "",
    kilometraje: "0",
    dias_mantenimiento: "90",
    observaciones: "",
    id_cliente: "",
    id_mecanico_asignado: "",
    id_marca: marca,
    id_tipo_combustible: combustible,
    id_tipo_unidad: unidad,
  };
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
  const [form, setForm] = useState(emptyForm());
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [search, setSearch] = useState("");

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
    return {
      marca: m.items[0] ? String(m.items[0].id) : "",
      combustible: c.items[0] ? String(c.items[0].id) : "",
      unidad: u.items[0] ? String(u.items[0].id) : "",
    };
  }, [auth, perms.can_manage_branch]);

  useEffect(() => {
    load();
    loadCatalogs();
  }, [load, loadCatalogs]);

  const openCreate = async () => {
    const defaults = await loadCatalogs();
    setForm(emptyForm(defaults?.marca, defaults?.combustible, defaults?.unidad));
    setError("");
    setCreateOpen(true);
  };

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
      setCreateOpen(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  const title = perms.is_cliente ? "Mis Vehículos" : "Vehículos";
  const createLabel = perms.is_cliente ? "+ Registrar vehículo" : "+ Nuevo vehículo";
  const hasData = rows.length > 0;

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (v) =>
        (v.placa ?? "").toLowerCase().includes(q)
        || (v.marca ?? "").toLowerCase().includes(q)
        || (v.modelo ?? "").toLowerCase().includes(q)
        || (v.cliente ?? "").toLowerCase().includes(q),
    );
  }, [rows, search]);

  return (
    <div className="page">
      <div className="page-header page-header-compact">
        <div>
          <h2>{title}</h2>
          <p className="page-subtitle">Flota registrada en la sucursal</p>
        </div>
        {hasData && (
          <div className="page-stat-inline">
            <span className="page-stat-value">{rows.length}</span>
            <span className="page-stat-label">vehículos</span>
          </div>
        )}
      </div>

      {error && !createOpen && <p className="error-text">{error}</p>}

      {!hasData ? (
        <EmptyState
          icon={<CarEmptyIcon />}
          title="No hay vehículos registrados"
          description="Registra la flota para poder agendar citas y dar seguimiento."
          action={
            <button type="button" className="btn" onClick={openCreate}>
              {perms.is_cliente ? "+ Registrar primer vehículo" : "+ Registrar primer vehículo"}
            </button>
          }
        />
      ) : (
        <div className="section-card">
          <ListToolbar
            search={search}
            onSearchChange={setSearch}
            placeholder="Buscar por placa, marca, modelo o cliente…"
            onAdd={openCreate}
            addLabel={createLabel}
          />
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
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={perms.is_cliente ? 6 : 7} className="table-no-results">
                      Sin resultados para “{search}”
                    </td>
                  </tr>
                ) : (
                  filtered.map((v) => (
                    <tr key={v.id}>
                      <td><span className="badge">{v.placa}</span></td>
                      <td>{v.marca}</td>
                      <td>{v.modelo}</td>
                      <td>{v.cliente}</td>
                      {!perms.is_cliente && <td>{v.mecanico_asignado || "—"}</td>}
                      <td>{v.numero_economico || "—"}</td>
                      <td>{v.kilometraje?.toLocaleString("es-MX") ?? "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <SidePanel
        open={createOpen}
        wide
        title={perms.is_cliente ? "Registrar vehículo" : "Nuevo vehículo"}
        onClose={() => setCreateOpen(false)}
        footer={
          <button type="button" className="btn btn-block" onClick={save}>
            Guardar vehículo
          </button>
        }
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-spaced">
          <div className="form-cols-2">
            <div className="form-row">
              <label>Placa</label>
              <input value={form.placa} onChange={(e) => setForm({ ...form, placa: e.target.value })} autoFocus />
            </div>
            <div className="form-row">
              <label>Número económico</label>
              <input value={form.numero_economico} onChange={(e) => setForm({ ...form, numero_economico: e.target.value })} />
            </div>
          </div>
          <div className="form-cols-2">
            <div className="form-row">
              <label>Serie</label>
              <input value={form.serie} onChange={(e) => setForm({ ...form, serie: e.target.value })} />
            </div>
            <div className="form-row">
              <label>Modelo</label>
              <input value={form.modelo} onChange={(e) => setForm({ ...form, modelo: e.target.value })} />
            </div>
          </div>
          <div className="form-cols-2">
            <div className="form-row">
              <label>Kilometraje</label>
              <input type="number" value={form.kilometraje} onChange={(e) => setForm({ ...form, kilometraje: e.target.value })} />
            </div>
            <div className="form-row">
              <label>Días mantenimiento</label>
              <input type="number" value={form.dias_mantenimiento} onChange={(e) => setForm({ ...form, dias_mantenimiento: e.target.value })} />
            </div>
          </div>
          <div className="form-cols-2">
            <div className="form-row">
              <label>Marca</label>
              <select value={form.id_marca} onChange={(e) => setForm({ ...form, id_marca: e.target.value })}>
                {marcas.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
              </select>
            </div>
            <div className="form-row">
              <label>Combustible</label>
              <select value={form.id_tipo_combustible} onChange={(e) => setForm({ ...form, id_tipo_combustible: e.target.value })}>
                {combustibles.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
              </select>
            </div>
          </div>
          <div className="form-row">
            <label>Tipo unidad</label>
            <select value={form.id_tipo_unidad} onChange={(e) => setForm({ ...form, id_tipo_unidad: e.target.value })}>
              {unidades.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
            </select>
          </div>
          {!perms.is_cliente && (
            <div className="form-row">
              <label>Propietario</label>
              <select value={form.id_cliente} onChange={(e) => setForm({ ...form, id_cliente: e.target.value })}>
                <option value="">Selecciona cliente</option>
                {clientes.map((c) => (
                  <option key={c.id} value={c.id}>{c.nombre}</option>
                ))}
              </select>
            </div>
          )}
          {perms.can_manage_branch && (
            <div className="form-row">
              <label>Mecánico asignado</label>
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
            <label>Observaciones</label>
            <textarea value={form.observaciones} onChange={(e) => setForm({ ...form, observaciones: e.target.value })} rows={3} />
          </div>
        </div>
      </SidePanel>
    </div>
  );
}
