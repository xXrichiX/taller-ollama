import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function ProfileMenu({ onLogout }: { onLogout: () => void }) {
  const { auth } = useAuth();
  if (!auth) return null;

  return (
    <div className="profile-chip">
      <div className="avatar">{auth.user.nombre.charAt(0).toUpperCase()}</div>
      <div className="profile-text">
        <strong>{auth.user.nombre}</strong>
        <span>{auth.role_label}</span>
        <span className="muted tiny">{auth.user.email}</span>
      </div>
      <button type="button" className="btn-ghost btn-sm" onClick={onLogout}>
        Cerrar sesión
      </button>
    </div>
  );
}
