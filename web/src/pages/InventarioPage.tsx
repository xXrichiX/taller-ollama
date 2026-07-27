import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { FormInput, FormSelect, FormTextarea } from "../components/forms";
import { ListToolbar } from "../components/ListToolbar";
import { Modal, ModalActions } from "../components/Modal";
import {
  parseDecimal,
  requireDecimal,
  requireText,
} from "../utils/formValidation";

interface InventarioItem {
  id: number;
  codigo?: string;
  nombre: string;
  descripcion?: string;
  cantidad: number;
  stock_minimo: number;
  precio_unitario: number;
  unidad: string;
  stock_bajo?: boolean;
}

const UNIDADES = [
  { value: "pza", label: "Pieza" },
  { value: "lt", label: "Litro" },
  { value: "kg", label: "Kilogramo" },
  { value: "jgo", label: "Juego" },
  { value: "caja", label: "Caja" },
];

function emptyForm() {
  return {
    codigo: "",
    nombre: "",
    descripcion: "",
    cantidad: "0",
    stock_minimo: "0",
    precio_unitario: "0",
    unidad: "pza",
  };
}

function formatMoney(n: number) {
  return n.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

export function InventarioPage() {
  const { auth } = useAuth();
  const [rows, setRows] = useState<InventarioItem[]>([]);
  const [form, setForm] = useState(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ items: InventarioItem[] }>("/api/inventario", {}, auth.token);
    setRows(res.items);
  }, [auth, auth?.user.id_isla]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.nombre.toLowerCase().includes(q)
        || (r.codigo ?? "").toLowerCase().includes(q)
        || (r.descripcion ?? "").toLowerCase().includes(q),
    );
  }, [rows, search]);

  const bajos = useMemo(() => rows.filter((r) => r.stock_bajo).length, [rows]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setError("");
    setModalOpen(true);
  };

  const openEdit = (item: InventarioItem) => {
    setEditingId(item.id);
    setForm({
      codigo: item.codigo ?? "",
      nombre: item.nombre,
      descripcion: item.descripcion ?? "",
      cantidad: String(item.cantidad),
      stock_minimo: String(item.stock_minimo),
      precio_unitario: String(item.precio_unitario),
      unidad: item.unidad || "pza",
    });
    setError("");
    setModalOpen(true);
  };

  const save = async () => {
    if (!auth) return;
    setError("");
    const err =
      requireText(form.nombre, "el nombre")
      || requireDecimal(form.cantidad, "El stock actual")
      || requireDecimal(form.stock_minimo, "El stock mínimo")
      || requireDecimal(form.precio_unitario, "El precio unitario");
    if (err) {
      setError(err);
      return;
    }
    const payload = {
      codigo: form.codigo,
      nombre: form.nombre.trim(),
      descripcion: form.descripcion,
      cantidad: parseDecimal(form.cantidad) ?? 0,
      stock_minimo: parseDecimal(form.stock_minimo) ?? 0,
      precio_unitario: parseDecimal(form.precio_unitario) ?? 0,
      unidad: form.unidad,
    };
    try {
      if (editingId) {
        await api(`/api/inventario/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        }, auth.token);
      } else {
        await api("/api/inventario", {
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

  const quickAdjust = async (id: number, delta: number) => {
    if (!auth) return;
    try {
      await api(`/api/inventario/${id}/ajustar`, {
        method: "POST",
        body: JSON.stringify({ delta }),
      }, auth.token);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al ajustar stock");
    }
  };

  return (
    <div className="page page-list">
      {error && !modalOpen && <p className="error-text">{error}</p>}

      {bajos > 0 && (
        <p className="inventario-alert">
          {bajos} artículo{bajos === 1 ? "" : "s"} con stock bajo o agotado
        </p>
      )}

      <div className="section-card">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          placeholder="Buscar por código, nombre o descripción…"
          onAdd={openCreate}
          addLabel="Nuevo artículo"
        />
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Artículo</th>
                <th>Stock</th>
                <th>Mínimo</th>
                <th>Precio</th>
                <th>Unidad</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr
                  key={r.id}
                  className={`clickable${r.stock_bajo ? " row-stock-bajo" : ""}`}
                  onClick={() => openEdit(r)}
                >
                  <td>{r.codigo || "—"}</td>
                  <td>
                    <span className="inventario-nombre">{r.nombre}</span>
                    {r.stock_bajo && <span className="status-pill status-pill-sm status-pill-warn">Stock bajo</span>}
                  </td>
                  <td>{r.cantidad}</td>
                  <td>{r.stock_minimo}</td>
                  <td>{formatMoney(r.precio_unitario)}</td>
                  <td>{UNIDADES.find((u) => u.value === r.unidad)?.label ?? r.unidad}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <div className="inventario-quick-actions">
                      <button type="button" className="btn-text btn-text-sm" onClick={() => quickAdjust(r.id, 1)} title="Entrada +1">+1</button>
                      <button type="button" className="btn-text btn-text-sm" onClick={() => quickAdjust(r.id, -1)} title="Salida -1">−1</button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="table-no-results">
                    {search ? "Sin resultados" : "Sin artículos en inventario"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={modalOpen}
        wide
        title={editingId ? "Editar artículo" : "Nuevo artículo"}
        onClose={() => setModalOpen(false)}
        footer={(
          <ModalActions
            onCancel={() => setModalOpen(false)}
            onSave={save}
            saveLabel={editingId ? "Guardar cambios" : "Agregar al inventario"}
          />
        )}
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-2col form-grid-spaced">
          <FormInput label="Código" value={form.codigo} onChange={(v) => setForm({ ...form, codigo: v })} placeholder="Opcional, ej. FIL-01" />
          <FormInput label="Nombre" value={form.nombre} onChange={(v) => setForm({ ...form, nombre: v })} placeholder="Ej. Filtro de aceite" autoFocus />
          <FormInput label="Stock actual" type="decimal" value={form.cantidad} onChange={(v) => setForm({ ...form, cantidad: v })} />
          <FormInput label="Stock mínimo" type="decimal" value={form.stock_minimo} onChange={(v) => setForm({ ...form, stock_minimo: v })} />
          <FormInput label="Precio unitario" type="decimal" value={form.precio_unitario} onChange={(v) => setForm({ ...form, precio_unitario: v })} />
          <FormSelect
            label="Unidad"
            value={form.unidad}
            onChange={(v) => setForm({ ...form, unidad: v })}
            options={UNIDADES}
            placeholder="Unidad"
          />
          <FormTextarea
            label="Descripción"
            value={form.descripcion}
            onChange={(v) => setForm({ ...form, descripcion: v })}
            placeholder="Marca, compatibilidad, notas…"
            className="form-span-2"
          />
        </div>
      </Modal>
    </div>
  );
}
