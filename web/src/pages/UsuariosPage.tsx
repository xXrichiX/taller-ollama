import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { EmptyState, UsersEmptyIcon } from "../components/EmptyState";
import { ListToolbar } from "../components/ListToolbar";
import { SidePanel } from "../components/SidePanel";
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

  const hasData = rows.length > 0;

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (u) =>
        u.nombre.toLowerCase().includes(q)
        || u.email.toLowerCase().includes(q)
        || (u.puesto ?? "").toLowerCase().includes(q),
    );
  }, [rows, search]);

  const formFields = (
    <>
      {error && <p className="error-text">{error}</p>}
      <div className="form-grid form-grid-spaced">
        <div className="form-row">
          <label>Nombre</label>
          <input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} disabled={!!editingId} />
        </div>
        <div className="form-row">
          <label>Email</label>
          <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} disabled={!!editingId} />
        </div>
        {!editingId && (
          <div className="form-row">
            <label>Contraseña</label>
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
        )}
        <div className="form-row">
          <label>Puesto</label>
          <select
            value={form.id_puesto}
            onChange={(e) => {
              const p = puestos.find((x) => x.id === Number(e.target.value));
              setForm({
                ...form,
                id_puesto: e.target.value,
                puesto_nombre: p?.nombre || "",
              });
            }}
          >
            {puestos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </div>
        <div className="form-row">
          <label>Sucursales (mecánico)</label>
          <p className="form-hint">Mantén Ctrl/Cmd para seleccionar varias.</p>
          <select
            multiple
            value={form.sucursales_ids.map(String)}
            onChange={(e) => {
              const ids = Array.from(e.target.selectedOptions).map((o) => Number(o.value));
              setForm({ ...form, sucursales_ids: ids });
            }}
            className="multi-select"
          >
            {sucursales.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}
          </select>
        </div>
      </div>
    </>
  );

  return (
    <div className="page">
      <div className="page-header page-header-compact">
        <div>
          <h2>Usuarios</h2>
          <p className="page-subtitle">Personal del taller y accesos al sistema</p>
        </div>
        {hasData && (
          <div className="page-stat-inline">
            <span className="page-stat-value">{rows.length}</span>
            <span className="page-stat-label">usuarios</span>
          </div>
        )}
      </div>

      {error && !panelOpen && <p className="error-text">{error}</p>}

      {!hasData ? (
        <EmptyState
          icon={<UsersEmptyIcon />}
          title="No hay usuarios registrados"
          description="Crea cuentas para mecánicos, recepción y administración del taller."
          action={
            <button type="button" className="btn" onClick={openCreate}>+ Registrar primer usuario</button>
          }
        />
      ) : (
        <div className="section-card">
          <ListToolbar
            search={search}
            onSearchChange={setSearch}
            placeholder="Buscar por nombre, email o puesto…"
            onAdd={openCreate}
            addLabel="Nuevo usuario"
          />
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr><th>Usuario</th><th>Email</th><th>Puesto</th><th>Sucursal</th></tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="table-no-results">Sin resultados para “{search}”</td>
                  </tr>
                ) : (
                  filtered.map((u) => (
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
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <SidePanel
        open={panelOpen}
        title={editingId ? "Editar usuario" : "Nuevo usuario"}
        onClose={() => { setPanelOpen(false); setEditingId(null); }}
        footer={
          <button type="button" className="btn btn-block" onClick={save}>
            {editingId ? "Guardar cambios" : "Crear usuario"}
          </button>
        }
      >
        {formFields}
      </SidePanel>
    </div>
  );
}
