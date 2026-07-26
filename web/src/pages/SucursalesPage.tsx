import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { FormInput } from "../components/forms";
import { ListToolbar } from "../components/ListToolbar";
import { Modal, ModalActions } from "../components/Modal";

interface Sucursal {
  id: number;
  nombre: string;
  direccion?: string;
  activo_label?: string;
}

export function SucursalesPage() {
  const { auth, setSucursal, refresh } = useAuth();
  const perms = usePermissions();
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [sucNombre, setSucNombre] = useState("");
  const [sucDir, setSucDir] = useState("");
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const loadSucursales = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ sucursales: Sucursal[] }>("/api/sucursales", {}, auth.token);
    setSucursales(res.sucursales);
  }, [auth]);

  useEffect(() => {
    loadSucursales();
  }, [loadSucursales]);

  useEffect(() => {
    if (perms.needs_taller_setup && sucursales.length === 0) {
      setCreateOpen(true);
    }
  }, [perms.needs_taller_setup, sucursales.length]);

  const createSucursal = async () => {
    if (!auth) return;
    setError("");
    try {
      const res = await api<{ ok: boolean; id: number }>("/api/sucursales", {
        method: "POST",
        body: JSON.stringify({ nombre: sucNombre, direccion: sucDir }),
      }, auth.token);
      setSucNombre("");
      setSucDir("");
      setCreateOpen(false);
      await refresh();
      await setSucursal(res.id);
      await loadSucursales();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  return (
    <div className="page page-list">
      {error && !createOpen && <p className="error-text">{error}</p>}

      <div className="section-card">
        {perms.can_create_sucursal && (
          <ListToolbar
            search=""
            onSearchChange={() => {}}
            showSearch={false}
            onAdd={() => { setError(""); setCreateOpen(true); }}
            addLabel="Nueva sucursal"
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
                  className={auth?.user.id_sucursal === s.id ? "row-selected" : "clickable"}
                  onClick={() => setSucursal(s.id)}
                >
                  <td>{s.nombre}</td>
                  <td>{s.direccion || "—"}</td>
                  <td>{s.activo_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={createOpen}
        wide
        title="Nueva sucursal"
        onClose={() => setCreateOpen(false)}
        footer={(
          <ModalActions
            onCancel={() => setCreateOpen(false)}
            onSave={createSucursal}
            saveLabel="Crear sucursal"
          />
        )}
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-2col form-grid-spaced">
          <FormInput label="Nombre" value={sucNombre} onChange={setSucNombre} placeholder="Ingresar nombre" autoFocus />
          <FormInput label="Dirección" value={sucDir} onChange={setSucDir} placeholder="Ingresar dirección" />
        </div>
      </Modal>
    </div>
  );
}
