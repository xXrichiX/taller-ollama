import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { FormInput, FormTextarea } from "../components/forms";
import { ListToolbar } from "../components/ListToolbar";
import { Modal, ModalActions } from "../components/Modal";
import { parseDecimal, requireDecimal, requireText } from "../utils/formValidation";

interface Servicio {
  id: number;
  nombre: string;
  descripcion?: string;
  precio: number;
}

function emptyForm() {
  return { nombre: "", descripcion: "", precio: "0" };
}

function formatMoney(n: number) {
  return n.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

export function ServiciosPage() {
  const { auth } = useAuth();
  const [rows, setRows] = useState<Servicio[]>([]);
  const [form, setForm] = useState(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ items: Servicio[] }>("/api/servicios", {}, auth.token);
    setRows(res.items);
  }, [auth]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.nombre.toLowerCase().includes(q)
        || (r.descripcion ?? "").toLowerCase().includes(q),
    );
  }, [rows, search]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setError("");
    setModalOpen(true);
  };

  const openEdit = (row: Servicio) => {
    setEditingId(row.id);
    setForm({
      nombre: row.nombre,
      descripcion: row.descripcion ?? "",
      precio: String(row.precio),
    });
    setError("");
    setModalOpen(true);
  };

  const save = async () => {
    if (!auth) return;
    setError("");
    const nombreErr = requireText(form.nombre, "el nombre del servicio");
    const precioErr = requireDecimal(form.precio, "El precio");
    const err = nombreErr || precioErr;
    if (err) {
      setError(err);
      return;
    }
    const payload = {
      nombre: form.nombre.trim(),
      descripcion: form.descripcion,
      precio: parseDecimal(form.precio) ?? 0,
    };
    try {
      if (editingId) {
        await api(`/api/servicios/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        }, auth.token);
      } else {
        await api("/api/servicios", {
          method: "POST",
          body: JSON.stringify(payload),
        }, auth.token);
      }
      setModalOpen(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  return (
    <div className="page page-list">
      {error && !modalOpen && <p className="error-text">{error}</p>}

      <div className="section-card">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          placeholder="Buscar servicio…"
          onAdd={openCreate}
          addLabel="Nuevo servicio"
        />
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Servicio</th>
                <th>Descripción</th>
                <th>Precio</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id} className="clickable" onClick={() => openEdit(s)}>
                  <td>{s.nombre}</td>
                  <td>{s.descripcion || "—"}</td>
                  <td>{formatMoney(s.precio)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={modalOpen}
        title={editingId ? "Editar servicio" : "Nuevo servicio"}
        onClose={() => setModalOpen(false)}
        footer={(
          <ModalActions
            onCancel={() => setModalOpen(false)}
            onSave={save}
            saveLabel="Guardar"
          />
        )}
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-spaced">
          <FormInput
            label="Nombre"
            value={form.nombre}
            onChange={(v) => setForm({ ...form, nombre: v })}
            placeholder="Ej. Cambio de aceite"
            autoFocus
          />
          <FormInput
            label="Precio"
            type="decimal"
            value={form.precio}
            onChange={(v) => setForm({ ...form, precio: v })}
          />
          <FormTextarea
            label="Descripción"
            value={form.descripcion}
            onChange={(v) => setForm({ ...form, descripcion: v })}
            placeholder="Qué incluye el servicio"
            className="form-span-2"
          />
        </div>
      </Modal>
    </div>
  );
}
