import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { FormInput, FormSelect, FormTextarea } from "../components/forms";
import { ListFilter, ListFilterSelect, uniqueColumnValues, useFilterModal } from "../components/ListFilter";
import { ListToolbar } from "../components/ListToolbar";
import { Modal, ModalActions } from "../components/Modal";

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
  const filters = useFilterModal({ marca: "", cliente: "", mecanico: "" });

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

  const createLabel = perms.is_cliente ? "Registrar vehículo" : "Nuevo vehículo";

  const marcaOptions = useMemo(() => uniqueColumnValues(rows, (v) => v.marca), [rows]);
  const clienteOptions = useMemo(() => uniqueColumnValues(rows, (v) => v.cliente), [rows]);
  const mecanicoOptions = useMemo(() => uniqueColumnValues(rows, (v) => v.mecanico_asignado), [rows]);
  const filtered = useMemo(() => {
    let list = rows;
    if (filters.applied.marca) list = list.filter((v) => (v.marca ?? "") === filters.applied.marca);
    if (filters.applied.cliente) list = list.filter((v) => (v.cliente ?? "") === filters.applied.cliente);
    if (filters.applied.mecanico) list = list.filter((v) => (v.mecanico_asignado ?? "") === filters.applied.mecanico);
    const q = search.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (v) =>
        (v.placa ?? "").toLowerCase().includes(q)
        || (v.marca ?? "").toLowerCase().includes(q)
        || (v.modelo ?? "").toLowerCase().includes(q)
        || (v.cliente ?? "").toLowerCase().includes(q)
        || (v.mecanico_asignado ?? "").toLowerCase().includes(q),
    );
  }, [rows, search, filters.applied]);

  return (
    <div className="page page-list">
      {error && !createOpen && <p className="error-text">{error}</p>}

      <div className="section-card">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          placeholder="Buscar por placa, marca, modelo o cliente…"
          onAdd={openCreate}
          addLabel={createLabel}
          filters={(
            <ListFilter
              open={filters.open}
              activeCount={filters.activeCount}
              draftActiveCount={filters.draftActiveCount}
              onOpen={filters.openFilter}
              onCancel={filters.cancelFilter}
              onSearch={filters.applyFilter}
              onClear={filters.clearFilters}
            >
              <ListFilterSelect
                label="Marca"
                value={filters.draft.marca}
                onChange={(v) => filters.setDraftField("marca", v)}
                options={marcaOptions}
              />
              <ListFilterSelect
                label="Cliente"
                value={filters.draft.cliente}
                onChange={(v) => filters.setDraftField("cliente", v)}
                options={clienteOptions}
              />
              {!perms.is_cliente && (
                <ListFilterSelect
                  label="Mecánico"
                  value={filters.draft.mecanico}
                  onChange={(v) => filters.setDraftField("mecanico", v)}
                  options={mecanicoOptions}
                />
              )}
            </ListFilter>
          )}
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
              {filtered.map((v) => (
                <tr key={v.id}>
                  <td><span className="badge">{v.placa}</span></td>
                  <td>{v.marca}</td>
                  <td>{v.modelo}</td>
                  <td>{v.cliente}</td>
                  {!perms.is_cliente && <td>{v.mecanico_asignado || "—"}</td>}
                  <td>{v.numero_economico || "—"}</td>
                  <td>{v.kilometraje?.toLocaleString("es-MX") ?? "—"}</td>
                </tr>
              ))}
              {filtered.length === 0 && (search || filters.activeCount > 0) && (
                <tr>
                  <td colSpan={perms.is_cliente ? 6 : 7} className="table-no-results">
                    Sin resultados con los filtros aplicados
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={createOpen}
        wide
        title={perms.is_cliente ? "Registrar vehículo" : "Nuevo vehículo"}
        onClose={() => setCreateOpen(false)}
        footer={
          <ModalActions
            onCancel={() => setCreateOpen(false)}
            onSave={save}
            saveLabel="Guardar vehículo"
          />
        }
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-2col form-grid-spaced">
          <FormInput label="Placa" value={form.placa} onChange={(v) => setForm({ ...form, placa: v })} placeholder="Ingresar placa" autoFocus />
          <FormInput label="Número económico" value={form.numero_economico} onChange={(v) => setForm({ ...form, numero_economico: v })} placeholder="Ingresar número" />
          <FormInput label="Serie" value={form.serie} onChange={(v) => setForm({ ...form, serie: v })} placeholder="Ingresar serie" />
          <FormInput label="Modelo" value={form.modelo} onChange={(v) => setForm({ ...form, modelo: v })} placeholder="Ingresar modelo" />
          <FormInput label="Kilometraje" type="number" value={form.kilometraje} onChange={(v) => setForm({ ...form, kilometraje: v })} />
          <FormInput label="Días mantenimiento" type="number" value={form.dias_mantenimiento} onChange={(v) => setForm({ ...form, dias_mantenimiento: v })} />
          <FormSelect
            label="Marca"
            value={form.id_marca}
            onChange={(v) => setForm({ ...form, id_marca: v })}
            options={marcas.map((m) => ({ value: String(m.id), label: m.nombre }))}
            placeholder="Seleccionar marca"
            searchable
          />
          <FormSelect
            label="Combustible"
            value={form.id_tipo_combustible}
            onChange={(v) => setForm({ ...form, id_tipo_combustible: v })}
            options={combustibles.map((m) => ({ value: String(m.id), label: m.nombre }))}
            placeholder="Seleccionar combustible"
          />
          <FormSelect
            label="Tipo unidad"
            value={form.id_tipo_unidad}
            onChange={(v) => setForm({ ...form, id_tipo_unidad: v })}
            options={unidades.map((m) => ({ value: String(m.id), label: m.nombre }))}
            placeholder="Seleccionar tipo"
          />
          {!perms.is_cliente && (
            <FormSelect
              label="Propietario"
              value={form.id_cliente}
              onChange={(v) => setForm({ ...form, id_cliente: v })}
              options={clientes.map((c) => ({ value: String(c.id), label: c.nombre }))}
              placeholder="Seleccionar cliente"
              searchable
            />
          )}
          {perms.can_manage_branch && (
            <FormSelect
              label="Mecánico asignado"
              value={form.id_mecanico_asignado}
              onChange={(v) => setForm({ ...form, id_mecanico_asignado: v })}
              options={mecanicos.map((m) => ({ value: String(m.id), label: m.nombre }))}
              placeholder="Sin asignar"
              searchable
            />
          )}
          <FormTextarea
            label="Observaciones"
            value={form.observaciones}
            onChange={(v) => setForm({ ...form, observaciones: v })}
            placeholder="Notas adicionales del vehículo"
            className="form-span-2"
          />
        </div>
      </Modal>
    </div>
  );
}
