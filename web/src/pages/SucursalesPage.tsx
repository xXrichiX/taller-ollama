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

interface Isla {
  id: number;
  nombre: string;
  activo_label?: string;
}

export function SucursalesPage() {
  const { auth, refresh } = useAuth();
  const perms = usePermissions();
  const [sucursales, setSucursales] = useState<Sucursal[]>([]);
  const [islas, setIslas] = useState<Isla[]>([]);
  const [islaNombre, setIslaNombre] = useState("");
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const sucursal = sucursales.find((s) => s.id === auth?.user.id_sucursal) ?? sucursales[0];

  const loadSucursales = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ sucursales: Sucursal[] }>("/api/sucursales", {}, auth.token);
    setSucursales(res.sucursales);
  }, [auth]);

  const loadIslas = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ islas: Isla[] }>("/api/islas", {}, auth.token);
    setIslas(res.islas);
  }, [auth]);

  useEffect(() => {
    loadSucursales();
    loadIslas();
  }, [loadSucursales, loadIslas]);

  const createIsla = async () => {
    if (!auth || !sucursal) return;
    setError("");
    try {
      await api(`/api/sucursales/${sucursal.id}/islas`, {
        method: "POST",
        body: JSON.stringify({ nombre: islaNombre }),
      }, auth.token);
      setIslaNombre("");
      setCreateOpen(false);
      await loadIslas();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  const canAdd = perms.can_manage_branch && Boolean(sucursal);

  return (
    <div className="page page-list">
      {error && !createOpen && <p className="error-text">{error}</p>}

      <div className="section-card">
        <ListToolbar
          search=""
          onSearchChange={() => {}}
          showSearch={false}
          onAdd={canAdd ? () => { setError(""); setCreateOpen(true); } : undefined}
          addLabel="Nueva isla"
        />
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Isla</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {islas.map((i) => (
                <tr key={i.id} className={auth?.user.id_isla === i.id ? "row-selected" : undefined}>
                  <td>{i.nombre}</td>
                  <td>{i.activo_label ?? "Sí"}</td>
                </tr>
              ))}
              {islas.length === 0 && (
                <tr>
                  <td colSpan={2} className="table-no-results">Sin islas — crea la primera bahía de trabajo</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Modal
        open={createOpen}
        title={`Nueva isla — ${sucursal?.nombre ?? "Taller"}`}
        onClose={() => setCreateOpen(false)}
        footer={(
          <ModalActions
            onCancel={() => setCreateOpen(false)}
            onSave={createIsla}
            saveLabel="Crear isla"
          />
        )}
      >
        {error && <p className="error-text">{error}</p>}
        <FormInput
          label="Nombre de la isla"
          value={islaNombre}
          onChange={setIslaNombre}
          placeholder="Ej. Isla 2, Bahía express…"
          autoFocus
        />
      </Modal>
    </div>
  );
}
