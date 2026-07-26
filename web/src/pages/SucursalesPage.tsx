import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { ListToolbar } from "../components/ListToolbar";
import { Modal, ModalActions } from "../components/Modal";

interface Sucursal {
  id: number;
  nombre: string;
  direccion?: string;
  activo_label?: string;
}

interface Isla {
  id: number;
  nombre: string;
  activo_label?: string;
}

export function SucursalesPage() {
  const { auth, setSucursal } = useAuth();
  const perms = usePermissions();
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [islas, setIslas] = useState<Isla[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sucNombre, setSucNombre] = useState("");
  const [sucDir, setSucDir] = useState("");
  const [islaNombre, setIslaNombre] = useState("");
  const [mecanicos, setMecanicos] = useState<Array<{ id: number; nombre: string }>>([]);
  const [islaMecId, setIslaMecId] = useState<number | "">("");
  const [error, setError] = useState("");
  const [sucursalOpen, setSucursalOpen] = useState(false);
  const [islaOpen, setIslaOpen] = useState(false);

  const selectedSucursal = sucursales.find((s) => s.id === selectedId);

  const loadSucursales = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ sucursales: Sucursal[] }>("/api/sucursales", {}, auth.token);
    setSucursales(res.sucursales);
    if (!selectedId && res.sucursales.length) setSelectedId(res.sucursales[0].id);
  }, [auth, selectedId]);

  const loadIslas = useCallback(async (id: number) => {
    if (!auth) return;
    const res = await api<{ islas: Isla[] }>(`/api/sucursales/${id}/islas`, {}, auth.token);
    setIslas(res.islas);
    const mec = await api<{ items: Array<{ id: number; nombre: string }> }>(
      "/api/catalogos/mecanicos",
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
  }, [selectedId, loadIslas]);

  const createSucursal = async () => {
    if (!auth) return;
    setError("");
    try {
      await api("/api/sucursales", {
        method: "POST",
        body: JSON.stringify({ nombre: sucNombre, direccion: sucDir }),
      }, auth.token);
      setSucNombre("");
      setSucDir("");
      setSucursalOpen(false);
      await loadSucursales();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
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
      setIslaOpen(false);
      await loadIslas(selectedId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  return (
    <div className="page">
      <div className="page-header page-header-compact">
        <div>
          <h2>Sucursales</h2>
          <p className="page-subtitle">Sucursales e islas de trabajo</p>
        </div>
        <div className="page-header-actions">
          <div className="page-stat-inline">
            <span className="page-stat-value">{sucursales.length}</span>
            <span className="page-stat-label">sucursales</span>
          </div>
        </div>
      </div>

      {error && !sucursalOpen && !islaOpen && <p className="error-text">{error}</p>}

      <div className="section-card">
        {perms.is_admin && (
          <ListToolbar
            search=""
            onSearchChange={() => {}}
            showSearch={false}
            onAdd={() => { setError(""); setSucursalOpen(true); }}
            addLabel="Nueva sucursal"
            action={
              <button
                type="button"
                className="btn-ghost btn-sm"
                onClick={() => { setError(""); setIslaOpen(true); }}
                disabled={!selectedId}
              >
                + Nueva isla
              </button>
            }
          />
        )}
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Dirección</th>
                <th>Activa</th>
              </tr>
            </thead>
            <tbody>
              {sucursales.map((s) => (
                <tr
                  key={s.id}
                  className={`clickable${selectedId === s.id ? " row-selected" : ""}`}
                  onClick={() => {
                    setSelectedId(s.id);
                    setSucursal(s.id);
                  }}
                >
                  <td>{s.nombre}</td>
                  <td>{s.direccion}</td>
                  <td>{s.activo_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-card">
        <div className="section-card-head">
          <h3>Islas — {selectedSucursal?.nombre ?? "Selecciona sucursal"}</h3>
          {perms.is_admin && selectedId && (
            <button type="button" className="btn-add" onClick={() => setIslaOpen(true)} title="Nueva isla" aria-label="Nueva isla">
              +
            </button>
          )}
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Isla</th><th>Activa</th></tr>
            </thead>
            <tbody>
              {islas.map((i) => (
                <tr key={i.id}>
                  <td>{i.nombre}</td>
                  <td>{i.activo_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={sucursalOpen}
        title="Nueva sucursal"
        onClose={() => setSucursalOpen(false)}
        footer={
          <ModalActions onCancel={() => setSucursalOpen(false)} onSave={createSucursal} saveLabel="Crear sucursal" />
        }
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-spaced">
          <div className="form-row">
            <label>Nombre</label>
            <input value={sucNombre} onChange={(e) => setSucNombre(e.target.value)} autoFocus />
          </div>
          <div className="form-row">
            <label>Dirección</label>
            <input value={sucDir} onChange={(e) => setSucDir(e.target.value)} />
          </div>
        </div>
      </Modal>

      <Modal
        open={islaOpen}
        title={`Nueva isla — ${selectedSucursal?.nombre ?? ""}`}
        onClose={() => setIslaOpen(false)}
        footer={
          <ModalActions onCancel={() => setIslaOpen(false)} onSave={createIsla} saveLabel="Crear isla" />
        }
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-spaced">
          <div className="form-row">
            <label>Nombre isla</label>
            <input value={islaNombre} onChange={(e) => setIslaNombre(e.target.value)} autoFocus />
          </div>
          <div className="form-row">
            <label>Mecánico (opcional)</label>
            <select
              value={islaMecId}
              onChange={(e) => setIslaMecId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">— Sin asignar —</option>
              {mecanicos.map((m) => (
                <option key={m.id} value={m.id}>{m.nombre}</option>
              ))}
            </select>
          </div>
        </div>
      </Modal>
    </div>
  );
}
