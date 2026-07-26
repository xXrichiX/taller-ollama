import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { ListToolbar } from "../components/ListToolbar";
import { Modal, ModalActions } from "../components/Modal";
import { getInitials } from "../utils/initials";

interface Cliente {
  id: number;
  nombre: string;
  telefono?: string;
  email?: string;
}

const EMPTY_FORM = { nombre: "", telefono: "", email: "" };

export function ClientesPage() {
  const { auth } = useAuth();
  const [rows, setRows] = useState<Cliente[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ clientes: Cliente[] }>("/api/clientes", {}, auth.token);
    setRows(res.clientes);
  }, [auth]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (c) =>
        c.nombre.toLowerCase().includes(q)
        || (c.telefono ?? "").toLowerCase().includes(q)
        || (c.email ?? "").toLowerCase().includes(q),
    );
  }, [rows, search]);

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setError("");
    setCreateOpen(true);
  };

  const save = async () => {
    if (!auth) return;
    setError("");
    try {
      await api("/api/clientes", {
        method: "POST",
        body: JSON.stringify(form),
      }, auth.token);
      setCreateOpen(false);
      setForm(EMPTY_FORM);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  return (
    <div className="page">
      <div className="page-header page-header-compact">
        <div>
          <h2>Clientes</h2>
          <p className="page-subtitle">Directorio de clientes del taller</p>
        </div>
        <div className="page-stat-inline">
          <span className="page-stat-value">{rows.length}</span>
          <span className="page-stat-label">registrados</span>
        </div>
      </div>

      {error && !createOpen && <p className="error-text">{error}</p>}

      <div className="section-card">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          placeholder="Buscar por nombre, teléfono o email…"
          onAdd={openCreate}
          addLabel="Nuevo cliente"
        />
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Cliente</th><th>Teléfono</th><th>Email</th></tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id}>
                  <td>
                    <div className="cell-user">
                      <span className="user-avatar">{getInitials(c.nombre)}</span>
                      <span>{c.nombre}</span>
                    </div>
                  </td>
                  <td>{c.telefono || "—"}</td>
                  <td>{c.email || "—"}</td>
                </tr>
              ))}
              {filtered.length === 0 && search && (
                <tr>
                  <td colSpan={3} className="table-no-results">Sin resultados para “{search}”</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={createOpen}
        title="Nuevo cliente"
        onClose={() => setCreateOpen(false)}
        footer={
          <ModalActions
            onCancel={() => setCreateOpen(false)}
            onSave={save}
            saveLabel="Guardar cliente"
          />
        }
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-spaced">
          <div className="form-row">
            <label>Nombre</label>
            <input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} autoFocus />
          </div>
          <div className="form-row">
            <label>Teléfono</label>
            <input value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} />
          </div>
          <div className="form-row">
            <label>Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
        </div>
      </Modal>
    </div>
  );
}
