import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { FormInput, FormSelect } from "../components/forms";
import { ListToolbar } from "../components/ListToolbar";
import { Modal, ModalActions } from "../components/Modal";

interface Sucursal {
  id: number;
  nombre: string;
}

interface Isla {
  id: number;
  nombre: string;
  activo_label?: string;
}

export function IslasPage() {
  const { auth, setSucursal } = useAuth();
  const perms = usePermissions();
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [islas, setIslas] = useState<Isla[]>([]);
  const [mecanicos, setMecanicos] = useState<Array<{ id: number; nombre: string }>>([]);
  const [islaNombre, setIslaNombre] = useState("");
  const [islaMecId, setIslaMecId] = useState<number | "">("");
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const selectedSucursal = sucursales.find((s) => s.id === selectedId);

  const loadSucursales = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ sucursales: Sucursal[] }>("/api/sucursales", {}, auth.token);
    setSucursales(res.sucursales);
    const active = auth.user.id_sucursal ?? res.sucursales[0]?.id ?? null;
    setSelectedId((prev) => prev ?? active);
  }, [auth]);

  const loadIslas = useCallback(async (id: number) => {
    if (!auth) return;
    const res = await api<{ islas: Isla[] }>(`/api/sucursales/${id}/islas`, {}, auth.token);
    setIslas(res.islas);
    const mec = await api<{ items: Array<{ id: number; nombre: string }> }>(
      `/api/catalogos/mecanicos?id_sucursal=${id}`,
      {},
      auth.token,
    );
    setMecanicos(mec.items);
  }, [auth]);

  useEffect(() => {
    loadSucursales();
  }, [loadSucursales]);

  useEffect(() => {
    if (selectedId) loadIslas(selectedId);
    else setIslas([]);
  }, [selectedId, loadIslas]);

  const onSucursalChange = async (id: number) => {
    setSelectedId(id);
    await setSucursal(id);
  };

  const createIsla = async () => {
    if (!auth || !selectedId) return;
    setError("");
    try {
      await api(`/api/sucursales/${selectedId}/islas`, {
        method: "POST",
        body: JSON.stringify({
          nombre: islaNombre,
          id_mecanico: islaMecId === "" ? null : islaMecId,
        }),
      }, auth.token);
      setIslaNombre("");
      setIslaMecId("");
      setCreateOpen(false);
      await loadIslas(selectedId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  const canAdd = perms.can_manage_branch && Boolean(selectedId);

  const sucursalFilter = sucursales.length > 0 ? (
    <div className="list-toolbar-filter">
      <label className="list-toolbar-filter-label" htmlFor="islas-sucursal">Sucursal</label>
      <select
        id="islas-sucursal"
        className="list-toolbar-filter-select"
        value={selectedId ?? ""}
        onChange={(e) => onSucursalChange(Number(e.target.value))}
        disabled={sucursales.length === 0}
      >
        {sucursales.length === 0 ? (
          <option value="">Sin sucursales</option>
        ) : (
          sucursales.map((s) => (
            <option key={s.id} value={s.id}>{s.nombre}</option>
          ))
        )}
      </select>
    </div>
  ) : undefined;

  return (
    <div className="page page-list">
      {error && !createOpen && <p className="error-text">{error}</p>}

      <div className="section-card">
        <ListToolbar
          search=""
          onSearchChange={() => {}}
          showSearch={false}
          filters={sucursalFilter}
          onAdd={canAdd ? () => { setError(""); setCreateOpen(true); } : undefined}
          addLabel="Nueva isla"
        />
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Isla</th>
                <th>Sucursal</th>
                <th>Activa</th>
              </tr>
            </thead>
            <tbody>
              {islas.map((i) => (
                <tr key={i.id}>
                  <td>{i.nombre}</td>
                  <td>{selectedSucursal?.nombre ?? "—"}</td>
                  <td>{i.activo_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={createOpen}
        wide
        title={`Nueva isla — ${selectedSucursal?.nombre ?? ""}`}
        onClose={() => setCreateOpen(false)}
        footer={(
          <ModalActions
            onCancel={() => setCreateOpen(false)}
            onSave={createIsla}
            mode="create"
          />
        )}
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-2col form-grid-spaced">
          <FormInput label="Nombre isla" value={islaNombre} onChange={setIslaNombre} placeholder="Ingresar nombre" autoFocus />
          <FormSelect
            label="Mecánico (opcional)"
            value={islaMecId === "" ? "" : String(islaMecId)}
            onChange={(v) => setIslaMecId(v ? Number(v) : "")}
            options={mecanicos.map((m) => ({ value: String(m.id), label: m.nombre }))}
            placeholder="Sin asignar"
            searchable
          />
        </div>
      </Modal>
    </div>
  );
}
