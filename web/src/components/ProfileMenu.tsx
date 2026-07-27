import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { FormInput } from "./forms";
import { Modal, ModalActions } from "./Modal";

export function ProfileMenu({ onLogout }: { onLogout: () => void }) {
  const { auth, refresh } = useAuth();
  const [open, setOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  const openProfile = () => {
    if (!auth) return;
    setNombre(auth.user.nombre);
    setEmail(auth.user.email);
    setPassword("");
    setError("");
    setOpen(false);
    setProfileOpen(true);
  };

  const saveProfile = async () => {
    if (!auth) return;
    setError("");
    setSaving(true);
    try {
      await api("/api/auth/perfil", {
        method: "PUT",
        body: JSON.stringify({ nombre, email, password }),
      }, auth.token);
      await refresh();
      setProfileOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  if (!auth) return null;

  const initial = auth.user.nombre.charAt(0).toUpperCase();

  return (
    <>
      <div className="profile-menu" ref={ref}>
        <button
          type="button"
          className="profile-trigger"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-haspopup="true"
        >
          <span className="avatar avatar-sm">{initial}</span>
          <span className="profile-trigger-name">{auth.user.nombre}</span>
          <span className="profile-chevron" aria-hidden>▾</span>
        </button>
        {open && (
          <div className="profile-dropdown">
            <button type="button" className="profile-dropdown-item" onClick={openProfile}>
              Mi perfil
            </button>
            <button
              type="button"
              className="profile-dropdown-item profile-dropdown-logout"
              onClick={() => {
                setOpen(false);
                onLogout();
              }}
            >
              Cerrar sesión
            </button>
          </div>
        )}
      </div>

      <Modal
        open={profileOpen}
        title="Mi perfil"
        onClose={() => setProfileOpen(false)}
        footer={(
          <ModalActions
            onCancel={() => setProfileOpen(false)}
            onSave={saveProfile}
            saveLabel="Guardar"
            saving={saving}
          />
        )}
      >
        {error && <p className="error-text">{error}</p>}
        <div className="form-grid form-grid-spaced">
          <FormInput
            label="Nombre"
            value={nombre}
            onChange={setNombre}
            placeholder="Tu nombre"
            autoFocus
          />
          <FormInput
            label="Correo"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="correo@gmail.com"
          />
          <FormInput
            label="Contraseña"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="Nueva contraseña (opcional)"
          />
        </div>
      </Modal>
    </>
  );
}
