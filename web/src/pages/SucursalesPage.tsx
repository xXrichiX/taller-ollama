import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";

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
      await loadIslas(selectedId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h2>Sucursales</h2>
      </div>
      {error && <p className="error-text">{error}</p>}
      <div className="split-layout">
        <div>
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
                    className="clickable"
                    onClick={() => {
                      setSelectedId(s.id);
                      setSucursal(s.id);
                    }}
                    style={{ background: selectedId === s.id ? "rgba(59,130,246,0.1)" : undefined }}
                  >
                    <td>{s.nombre}</td>
                    <td>{s.direccion}</td>
                    <td>{s.activo_label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3 className="section-title">Islas de la sucursal</h3>
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
        {perms.is_admin && (
          <div className="side-panel">
            <h3>Nueva sucursal</h3>
            <div className="form-grid">
              <div className="form-row">
                <label>Nombre</label>
                <input value={sucNombre} onChange={(e) => setSucNombre(e.target.value)} />
              </div>
              <div className="form-row">
                <label>Dirección</label>
                <input value={sucDir} onChange={(e) => setSucDir(e.target.value)} />
              </div>
              <button className="btn" onClick={createSucursal}>Crear sucursal</button>
            </div>
            <h3 style={{ marginTop: "1.25rem" }}>Nueva isla</h3>
            <div className="form-grid">
              <div className="form-row">
                <label>Nombre isla</label>
                <input value={islaNombre} onChange={(e) => setIslaNombre(e.target.value)} />
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
              <button className="btn" onClick={createIsla}>Crear isla</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
