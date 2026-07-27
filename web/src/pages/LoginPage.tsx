import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppLoader } from "../components/AppLoader";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { login, register, auth, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (auth) navigate("/", { replace: true });
  }, [auth, navigate]);

  if (authLoading) {
    return <AppLoader />;
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(nombre, email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-brand">IESPRO</h1>
        <form onSubmit={submit} className="form-grid">
          {mode === "register" && (
            <div className="form-row">
              <label htmlFor="login-nombre">Nombre</label>
              <input
                id="login-nombre"
                className="login-input"
                placeholder="Tu nombre completo"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                required
              />
            </div>
          )}
          <div className="form-row">
            <label htmlFor="login-email">Correo</label>
            <input
              id="login-email"
              className="login-input"
              type="email"
              placeholder="correo@gmail.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="form-row">
            <label htmlFor="login-password">Contraseña</label>
            <div className="password-field">
              <input
                id="login-password"
                className="login-input"
                type={showPassword ? "text" : "password"}
                placeholder="Mínimo 8 caracteres y un número"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                title={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
              >
                {showPassword ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M3 3l18 18M10.58 10.58A2 2 0 0012 15a2 2 0 001.41-3.41M9.88 4.24A10.94 10.94 0 0112 5c5 0 9.27 3.11 11 7a11.8 11.8 0 01-4.12 4.88M6.61 6.61A11.33 11.33 0 003 12c1.73 3.89 6 7 11 7 1.74 0 3.37-.42 4.82-1.16"
                      stroke="currentColor"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                    />
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path
                      d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"
                      stroke="currentColor"
                      strokeWidth="1.75"
                    />
                    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.75" />
                  </svg>
                )}
              </button>
            </div>
          </div>
          {error && <p className="error-text">{error}</p>}
          <button className="btn btn-with-loader" type="submit" disabled={loading}>
            {loading && <span className="btn-spinner" aria-hidden />}
            {loading
              ? (mode === "login" ? "Entrando…" : "Creando cuenta…")
              : (mode === "login" ? "Entrar" : "Crear cuenta")}
          </button>
        </form>
        <p className="muted" style={{ marginTop: "1rem", textAlign: "center" }}>
          {mode === "login" ? "¿No tienes cuenta? " : "¿Ya tienes cuenta? "}
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              setMode(mode === "login" ? "register" : "login");
            }}
          >
            {mode === "login" ? "Regístrate" : "Inicia sesión"}
          </a>
        </p>
      </div>
    </div>
  );
}
