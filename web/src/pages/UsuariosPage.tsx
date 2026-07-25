import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

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

export function UsuariosPage() {
  const { auth } = useAuth();
  const [rows, setRows] = useState<Usuario[]>([]);
  const [puestos, setPuestos] = useState<CatalogItem[]>([]);
  const [sucursales, setSucursales] = useState<CatalogItem[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({
    nombre: "",
    email: "",
    password: "pass1234",
    id_puesto: "",
    puesto_nombre: "",
    sucursales_ids: [] as number[],
  });
  const [error, setError] = useState("");

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
    if (p.items.length && !form.id_puesto) {
      setForm((f) => ({
        ...f,
        id_puesto: String(p.items[0].id),
        puesto_nombre: p.items[0].nombre,
      }));
    }
  }, [auth, form.id_puesto]);

  useEffect(() => {
    load();
  }, [load]);

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
      setEditingId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Usuarios</h2>
        <button className="btn-ghost" onClick={() => {
          setEditingId(null);
          setForm({ nombre: "", email: "", password: "pass1234", id_puesto: "", puesto_nombre: "", sucursales_ids: [] });
        }}>
          + Crear usuario
        </button>
      </div>
      {error && <p className="error-text">{error}</p>}
      <div className="split-layout">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Nombre</th><th>Email</th><th>Puesto</th><th>Sucursal</th></tr>
            </thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.id} className="clickable" onClick={() => selectUser(u.id)}>
                  <td>{u.nombre}</td>
                  <td>{u.email}</td>
                  <td>{u.puesto}</td>
                  <td>{u.sucursal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="side-panel">
          <h3>{editingId ? "Editar usuario" : "Nuevo usuario"}</h3>
          <div className="form-grid">
            <div className="form-row">
              <label>Nombre</label>
              <input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} disabled={!!editingId} />
            </div>
            <div className="form-row">
              <label>Email</label>
              <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} disabled={!!editingId} />
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
              <select
                multiple
                value={form.sucursales_ids.map(String)}
                onChange={(e) => {
                  const ids = Array.from(e.target.selectedOptions).map((o) => Number(o.value));
                  setForm({ ...form, sucursales_ids: ids });
                }}
                style={{ minHeight: "100px" }}
              >
                {sucursales.map((s) => <option key={s.id} value={s.id}>{s.nombre}</option>)}
              </select>
            </div>
            <button className="btn" onClick={save}>Guardar</button>
          </div>
        </div>
      </div>
    </div>
  );
}
