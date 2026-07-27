import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { FormInput, FormMultiSelect, FormSelect } from "../components/forms";
import { ListFilter, ListFilterSelect, uniqueColumnValues, useFilterModal } from "../components/ListFilter";
import { ListToolbar } from "../components/ListToolbar";
import { Modal, ModalActions } from "../components/Modal";
import { getInitials } from "../utils/initials";

interface Usuario {
  id: number;
  nombre: string;
  email: string;
  puesto?: string;
  sucursal?: string;
}

interface CatalogItem {
  id: number;
  nombre: string;
}

function emptyForm(defaultPuesto = "", defaultPuestoNombre = "") {
  return {
    nombre: "",
    email: "",
    password: "pass1234",
    id_puesto: defaultPuesto,
    puesto_nombre: defaultPuestoNombre,
    sucursales_ids: [] as number[],
  };
}

export function UsuariosPage() {
  const { auth } = useAuth();
  const [rows, setRows] = useState<Usuario[]>([]);
  const [puestos, setPuestos] = useState<CatalogItem[]>([]);
  const [sucursales, setSucursales] = useState<CatalogItem[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm());
  const [error, setError] = useState("");
  const [panelOpen, setPanelOpen] = useState(false);
  const [search, setSearch] = useState("");
  const filters = useFilterModal({ puesto: "", sucursal: "" });

  const load = useCallback(async () => {
    if (!auth) return;
    const [u, p, s] = await Promise.all([
      api<{ usuarios: Usuario[] }>("/api/usuarios", {}, auth.token),
      api<{ items: CatalogItem[] }>("/api/catalogos/puestos", {}, auth.token),
      api<{ sucursales: CatalogItem[] }>("/api/sucursales", {}, auth.token),
    ]);
    setRows(u.usuarios);
    setPuestos(p.items);
    setSucursales(s.sucursales);
    return p.items[0];
  }, [auth]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = async () => {
    const first = puestos[0] ?? (await load());
    setEditingId(null);
    setForm(emptyForm(first ? String(first.id) : "", first?.nombre ?? ""));
    setError("");
    setPanelOpen(true);
  };

  const selectUser = async (id: number) => {
    if (!auth) return;
    const u = rows.find((r) => r.id === id);
    if (!u) return;
    setEditingId(id);
    const suc = await api<{ sucursales: CatalogItem[] }>(`/api/usuarios/${id}/sucursales`, {}, auth.token);
    const puesto = puestos.find((p) => p.nombre === u.puesto);
    setForm({
      nombre: u.nombre,
      email: u.email,
      password: "",
      id_puesto: puesto ? String(puesto.id) : "",
      puesto_nombre: u.puesto || "",
      sucursales_ids: suc.sucursales.map((s) => s.id),
    });
    setError("");
    setPanelOpen(true);
  };

  const save = async () => {
    if (!auth) return;
    setError("");
    try {
      if (editingId) {
        await api(`/api/usuarios/${editingId}/staff`, {
          method: "PATCH",
          body: JSON.stringify({
            id_puesto: Number(form.id_puesto),
            puesto_nombre: form.puesto_nombre,
            sucursales_ids: form.sucursales_ids,
          }),
        }, auth.token);
      } else {
        await api("/api/usuarios", {
          method: "POST",
          body: JSON.stringify({
            nombre: form.nombre,
            email: form.email,
            password: form.password,
            id_puesto: Number(form.id_puesto),
            puesto_nombre: form.puesto_nombre,
            sucursales_ids: form.sucursales_ids,
          }),
        }, auth.token);
      }
      setPanelOpen(false);
      setEditingId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  const puestoOptions = useMemo(() => uniqueColumnValues(rows, (u) => u.puesto), [rows]);
  const sucursalOptions = useMemo(() => uniqueColumnValues(rows, (u) => u.sucursal), [rows]);
  const filtered = useMemo(() => {
    let list = rows;
    if (filters.applied.puesto) list = list.filter((u) => u.puesto === filters.applied.puesto);
    if (filters.applied.sucursal) list = list.filter((u) => (u.sucursal ?? "") === filters.applied.sucursal);
    const q = search.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (u) =>
        u.nombre.toLowerCase().includes(q)
        || u.email.toLowerCase().includes(q)
        || (u.puesto ?? "").toLowerCase().includes(q)
        || (u.sucursal ?? "").toLowerCase().includes(q),
    );
  }, [rows, search, filters.applied]);

  const formFields = (
    <>
      {error && <p className="error-text">{error}</p>}
      <div className="form-grid form-grid-2col form-grid-spaced">
        <FormInput
          label="Nombre"
          value={form.nombre}
          onChange={(v) => setForm({ ...form, nombre: v })}
          placeholder="Ingresar nombre"
          disabled={!!editingId}
        />
        <FormInput
          label="Email"
          type="email"
          value={form.email}
          onChange={(v) => setForm({ ...form, email: v })}
          placeholder="Ingresar correo"
          disabled={!!editingId}
        />
        {!editingId && (
          <FormInput
            label="Contraseña"
            type="password"
            value={form.password}
            onChange={(v) => setForm({ ...form, password: v })}
            placeholder="Ingresar contraseña"
            className="form-span-2"
          />
        )}
        <FormSelect
          label="Puesto"
          value={form.id_puesto}
          onChange={(v) => {
            const p = puestos.find((x) => x.id === Number(v));
            setForm({
              ...form,
              id_puesto: v,
              puesto_nombre: p?.nombre || "",
            });
          }}
          options={puestos.map((p) => ({ value: String(p.id), label: p.nombre }))}
          placeholder="Seleccionar puesto"
          className="form-span-2"
        />
        <FormMultiSelect
          label="Sucursales (mecánico)"
          values={form.sucursales_ids}
          onChange={(ids) => setForm({ ...form, sucursales_ids: ids })}
          placeholder="Seleccionar sucursales"
          className="form-span-2"
          options={sucursales.map((s) => ({ value: String(s.id), label: s.nombre }))}
        />
      </div>
    </>
  );

  return (
    <div className="page page-list">
      {error && !panelOpen && <p className="error-text">{error}</p>}

      <div className="section-card">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          placeholder="Buscar por nombre, email o puesto…"
          onAdd={openCreate}
          addLabel="Nuevo usuario"
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
                label="Puesto"
                value={filters.draft.puesto}
                onChange={(v) => filters.setDraftField("puesto", v)}
                options={puestoOptions}
              />
              <ListFilterSelect
                label="Sucursal"
                value={filters.draft.sucursal}
                onChange={(v) => filters.setDraftField("sucursal", v)}
                options={sucursalOptions}
              />
            </ListFilter>
          )}
        />
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Usuario</th><th>Email</th><th>Puesto</th><th>Sucursal</th></tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id} className="clickable" onClick={() => selectUser(u.id)}>
                  <td>
                    <div className="cell-user">
                      <span className="user-avatar">{getInitials(u.nombre)}</span>
                      <span>{u.nombre}</span>
                    </div>
                  </td>
                  <td>{u.email}</td>
                  <td>{u.puesto}</td>
                  <td>{u.sucursal || "—"}</td>
                </tr>
              ))}
              {filtered.length === 0 && (search || filters.activeCount > 0) && (
                <tr>
                  <td colSpan={4} className="table-no-results">Sin resultados con los filtros aplicados</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={panelOpen}
        wide
        title={editingId ? "Editar usuario" : "Nuevo usuario"}
        onClose={() => { setPanelOpen(false); setEditingId(null); }}
        footer={
          <ModalActions
            onCancel={() => { setPanelOpen(false); setEditingId(null); }}
            onSave={save}
            mode={editingId ? "edit" : "create"}
          />
        }
      >
        {formFields}
      </Modal>
    </div>
  );
}
