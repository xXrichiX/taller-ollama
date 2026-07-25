import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

interface Cliente {
  id: number;
  nombre: string;
  telefono?: string;
  email?: string;
}

export function ClientesPage() {
  const { auth } = useAuth();
  const [rows, setRows] = useState<Cliente[]>([]);
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ clientes: Cliente[] }>("/api/clientes", {}, auth.token);
    setRows(res.clientes);
  }, [auth]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    if (!auth) return;
    setError("");
    try {
      await api("/api/clientes", {
        method: "POST",
        body: JSON.stringify({ nombre, telefono, email }),
      }, auth.token);
      setNombre("");
      setTelefono("");
      setEmail("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    }
  };

  return (
    <div className="page">
      <div className="page-header"><h2>Clientes</h2></div>
      {error && <p className="error-text">{error}</p>}
      <div className="split-layout">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Nombre</th><th>Teléfono</th><th>Email</th></tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id}>
                  <td>{c.nombre}</td>
                  <td>{c.telefono}</td>
                  <td>{c.email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="side-panel">
          <h3>Nuevo cliente</h3>
          <div className="form-grid">
            <div className="form-row">
              <label>Nombre</label>
              <input value={nombre} onChange={(e) => setNombre(e.target.value)} />
            </div>
            <div className="form-row">
              <label>Teléfono</label>
              <input value={telefono} onChange={(e) => setTelefono(e.target.value)} />
            </div>
            <div className="form-row">
              <label>Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <button className="btn" onClick={save}>Guardar cliente</button>
          </div>
        </div>
      </div>
    </div>
  );
}
