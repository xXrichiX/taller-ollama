import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";

export function ProfileMenu({ onLogout }: { onLogout: () => void }) {
  const { auth } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  if (!auth) return null;

  const initial = auth.user.nombre.charAt(0).toUpperCase();

  return (
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
          <div className="profile-dropdown-head">
            <strong>{auth.user.nombre}</strong>
            <span className="profile-dropdown-role">{auth.role_label}</span>
            <span className="profile-dropdown-email">{auth.user.email}</span>
          </div>
          <button type="button" className="profile-dropdown-item" onClick={() => setOpen(false)}>
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
  );
}
