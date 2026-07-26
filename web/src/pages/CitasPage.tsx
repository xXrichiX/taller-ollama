import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { ListFilter, ListFilterSelect, uniqueColumnValues, useFilterModal } from "../components/ListFilter";
import { ListToolbar } from "../components/ListToolbar";
import { Modal, ModalActions } from "../components/Modal";
import {
  FormInput,
  FormMultiSelect,
  FormSelect,
  TimeSelect,
} from "../components/forms";
import { estadoPillClass } from "../utils/ordenStatus";

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
    servicio_ids: [] as number[],
  });
  const [manage, setManage] = useState({
    estado: "",
    diagnostico: "",
    observaciones: "",
    solucion: "",
  });
  const [error, setError] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [search, setSearch] = useState("");
  const filters = useFilterModal({ estado: "" });

  const load = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ citas: Cita[] }>("/api/citas", {}, auth.token);
    setRows(res.citas);
  }, [auth, auth?.user.id_isla]);

  const loadFormData = useCallback(async () => {
    if (!auth) return;
    const est = await api<{ items: string[] }>("/api/catalogos/estados-cita", {}, auth.token);
    setEstados(est.items);
    if (!perms.is_cliente) {
      const cl = await api<{ clientes: CatalogItem[] }>("/api/clientes", {}, auth.token);
      setClientes(cl.clientes);
    }
    if (perms.is_staff) {
      const s = await api<{ items: Array<{ id: number; nombre: string; precio?: number }> }>(
        "/api/catalogos/mantenimiento",
        {},
        auth.token,
      );
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

  const createLabel = perms.is_cliente ? "Solicitar servicio" : "Nueva orden";
  const canCreate = perms.can_create_citas || perms.is_cliente;

  const estadoOptions = useMemo(() => uniqueColumnValues(rows, (c) => c.estado_label), [rows]);
  const filtered = useMemo(() => {
    let list = rows;
    if (filters.applied.estado) list = list.filter((c) => c.estado_label === filters.applied.estado);
    const q = search.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (c) =>
        (c.cliente ?? "").toLowerCase().includes(q)
        || (c.placa ?? "").toLowerCase().includes(q)
        || (c.estado_label ?? "").toLowerCase().includes(q)
        || (c.descripcion_fallo ?? "").toLowerCase().includes(q),
    );
  }, [rows, search, filters.applied]);

  return (
    <div className="page page-list">
      {error && <p className="error-text">{error}</p>}

      <div className="section-card">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          placeholder="Buscar por cliente, placa, estado o falla…"
          onAdd={canCreate ? () => setCreateOpen(true) : undefined}
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
                label="Estado"
                value={filters.draft.estado}
                onChange={(v) => filters.setDraftField("estado", v)}
                options={estadoOptions}
              />
            </ListFilter>
          )}
        />
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                {!perms.is_cliente && <th>Cliente</th>}
                <th>Placa</th>
                <th>Fecha</th>
                <th>Estado</th>
                <th>Falla</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr
                  key={c.id}
                  className={perms.can_manage_citas ? "clickable" : ""}
                  onClick={() => perms.can_manage_citas && openCita(c.id)}
                >
                  {!perms.is_cliente && <td>{c.cliente}</td>}
                  <td><span className="badge">{c.placa}</span></td>
                  <td>{c.fecha_cita}</td>
                  <td><span className={estadoPillClass(c.estado_label)}>{c.estado_label}</span></td>
                  <td className="truncate">{c.descripcion_fallo}</td>
                </tr>
              ))}
              {filtered.length === 0 && (search || filters.activeCount > 0) && (
                <tr>
                  <td colSpan={perms.is_cliente ? 4 : 5} className="table-no-results">
                    Sin resultados con los filtros aplicados
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={drawerOpen && selected !== null && perms.can_manage_citas}
        wide
        title={`Orden #${selected ?? ""}`}
        onClose={() => { setDrawerOpen(false); setSelected(null); setDetail(null); }}
        footer={
          detail ? (
            <ModalActions
              onCancel={() => { setDrawerOpen(false); setSelected(null); setDetail(null); }}
              onSave={updateCita}
              saveLabel="Guardar cambios"
            />
          ) : undefined
        }
      >
        {detail && (
          <>
            <p className="modal-context">
              Falla reportada: {String(detail.cita.descripcion_fallo || "—")}
            </p>
            <div className="form-grid form-grid-2col form-grid-spaced">
              <FormSelect
                label="Estado de la orden"
                value={manage.estado}
                onChange={(v) => setManage({ ...manage, estado: v })}
                options={estados.map((e) => ({ value: e, label: e }))}
                placeholder="Seleccionar estado"
              />
              <FormInput
                label="Diagnóstico"
                value={manage.diagnostico}
                onChange={(v) => setManage({ ...manage, diagnostico: v })}
                placeholder="Ingresar diagnóstico"
              />
              <FormInput
                label="Observaciones"
                value={manage.observaciones}
                onChange={(v) => setManage({ ...manage, observaciones: v })}
                placeholder="Ingresar observaciones"
                className="form-span-2"
              />
              <FormInput
                label="Solución"
                value={manage.solucion}
                onChange={(v) => setManage({ ...manage, solucion: v })}
                placeholder="Ingresar solución aplicada"
                className="form-span-2"
              />
            </div>
          </>
        )}
      </Modal>

      <Modal
        open={createOpen}
        wide
        title={perms.is_cliente ? "Solicitar servicio" : "Nueva orden de servicio"}
        onClose={() => setCreateOpen(false)}
        footer={
          <ModalActions
            onCancel={() => setCreateOpen(false)}
            onSave={async () => {
              await createCita();
              setCreateOpen(false);
            }}
            saveLabel={perms.is_cliente ? "Solicitar" : "Registrar orden"}
          />
        }
      >
        <div className="form-grid form-grid-2col form-grid-spaced">
          {!perms.is_cliente && (
            <FormSelect
              label="Cliente"
              value={form.id_cliente}
              onChange={onClienteChange}
              options={clientes.map((c) => ({ value: String(c.id), label: c.nombre }))}
              placeholder="Seleccionar cliente"
              searchable
            />
          )}
          <FormSelect
            label="Vehículo"
            value={form.id_vehiculo}
            onChange={(v) => setForm({ ...form, id_vehiculo: v })}
            options={vehiculos.map((v) => ({
              value: String(v.id),
              label: `${v.placa} — ${v.marca} ${v.modelo}`,
            }))}
            placeholder="Seleccionar vehículo"
            searchable
            className={perms.is_cliente ? "form-span-2" : ""}
          />
          <FormInput
            label="Fecha cita"
            type="date"
            value={form.fecha_cita}
            onChange={(v) => setForm({ ...form, fecha_cita: v })}
          />
          <TimeSelect
            label="Hora cita"
            value={form.hora_cita}
            onChange={(v) => setForm({ ...form, hora_cita: v })}
          />
          <FormInput
            label="Descripción fallo"
            value={form.descripcion_fallo}
            onChange={(v) => setForm({ ...form, descripcion_fallo: v })}
            placeholder="Describe el problema del vehículo"
            className="form-span-2"
          />
          <FormInput
            label="Fecha compromiso"
            type="date"
            value={form.fecha_compromiso}
            onChange={(v) => setForm({ ...form, fecha_compromiso: v })}
          />
          <TimeSelect
            label="Hora compromiso"
            value={form.hora_compromiso}
            onChange={(v) => setForm({ ...form, hora_compromiso: v })}
            withSeconds
          />
          <FormMultiSelect
            label="Mantenimiento"
            values={form.servicio_ids}
            onChange={(ids) => setForm({ ...form, servicio_ids: ids })}
            placeholder="Seleccionar servicios"
            className="form-span-2"
            options={servicios.map((s) => ({
              value: String(s.id),
              label: s.nombre,
              meta: s.precio != null ? `$${s.precio}` : undefined,
            }))}
          />
        </div>
      </Modal>
    </div>
  );
}
