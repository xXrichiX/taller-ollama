import { Turnstile, type TurnstileInstance } from "@marsidev/react-turnstile";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppLoader } from "../components/AppLoader";
import { ApiError, fetchPublicAuthConfig, type PublicAuthConfig } from "../api/client";
import { useAuth } from "../context/AuthContext";

const LOGIN_COOLDOWN_SEC = 30;
const REGISTER_COOLDOWN_SEC = 30;

export function LoginPage() {
  const { login, register, auth, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nombre, setNombre] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [publicConfig, setPublicConfig] = useState<PublicAuthConfig | null>(null);
  const [captchaToken, setCaptchaToken] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const turnstileRef = useRef<TurnstileInstance | null>(null);

  useEffect(() => {
    fetchPublicAuthConfig()
      .then(setPublicConfig)
      .catch(() =>
        setPublicConfig({
          registration_enabled: false,
          turnstile_site_key: "",
          invite_required: false,
          captcha_mode: "none",
          email_verification_enabled: false,
        }),
      );
  }, []);

  useEffect(() => {
    if (auth) navigate("/", { replace: true });
  }, [auth, navigate]);

  useEffect(() => {
    setCaptchaToken("");
    turnstileRef.current?.reset();
    setSuccess("");
  }, [mode]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setInterval(() => {
      setCooldown((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  useEffect(() => {
    if (cooldown === 0 && error.includes("Demasiadas peticiones")) {
      setError("");
    }
  }, [cooldown, error]);

  if (authLoading) {
    return <AppLoader />;
  }

  const registrationEnabled = publicConfig?.registration_enabled ?? false;
  const turnstileSiteKey =
    (import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined)?.trim()
    || publicConfig?.turnstile_site_key
    || "";
  const turnstileActive =
    Boolean(turnstileSiteKey)
    || publicConfig?.captcha_configured === true
    || publicConfig?.captcha_mode === "turnstile";
  const inviteRequired = publicConfig?.invite_required ?? false;
  const blocked = cooldown > 0;

  const startCooldown = (seconds: number, message?: string) => {
    setCooldown(seconds);
    setError(message ?? "Demasiadas peticiones. Espera a que termine el contador.");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (blocked) return;

    setError("");
    setSuccess("");
    if (mode === "register" && turnstileSiteKey && !captchaToken) {
      setError("No se pudo completar la verificación.");
      return;
    }

    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
        navigate("/", { replace: true });
      } else {
        const message = await register(nombre, email, password, {
          inviteCode,
          captchaToken,
        });
        setPassword("");
        setNombre("");
        setInviteCode("");
        setMode("login");
        setSuccess(message || "Cuenta creada. Ya puedes iniciar sesión.");
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        const seconds = err.retryAfterSec
          ?? (mode === "login" ? LOGIN_COOLDOWN_SEC : REGISTER_COOLDOWN_SEC);
        startCooldown(seconds);
      } else {
        setError(err instanceof Error ? err.message : "Error");
      }
      turnstileRef.current?.reset();
      setCaptchaToken("");
    } finally {
      setLoading(false);
    }
  };

  const buttonLabel = blocked
    ? `Espera ${cooldown}s para reintentar`
    : loading
      ? (mode === "login" ? "Entrando…" : "Creando cuenta…")
      : (mode === "login" ? "Entrar" : "Crear cuenta");

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-brand">Taller</h1>
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
                disabled={blocked}
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
              disabled={blocked}
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
                disabled={blocked}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                title={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                disabled={blocked}
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
          {mode === "register" && inviteRequired && (
            <div className="form-row">
              <label htmlFor="login-invite">Código de invitación</label>
              <input
                id="login-invite"
                className="login-input"
                placeholder="Código proporcionado por el administrador"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                required
                disabled={blocked}
              />
            </div>
          )}
          {mode === "register" && turnstileSiteKey && (
            <div className="form-row turnstile-row">
              <Turnstile
                ref={turnstileRef}
                siteKey={turnstileSiteKey}
                onSuccess={setCaptchaToken}
                onExpire={() => setCaptchaToken("")}
              />
            </div>
          )}
          {success && <p className="success-text">{success}</p>}
          {error && <p className="error-text">{error}</p>}
          <button
            className="btn btn-with-loader"
            type="submit"
            disabled={loading || blocked}
          >
            {loading && <span className="btn-spinner" aria-hidden />}
            {buttonLabel}
          </button>
        </form>
        <p className="muted" style={{ marginTop: "1rem", textAlign: "center" }}>
          {(mode === "login" ? registrationEnabled : true) && (
            <>
              {mode === "login" ? "¿No tienes cuenta? " : "¿Ya tienes cuenta? "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  if (blocked) return;
                  if (mode === "login" && !registrationEnabled) return;
                  setMode(mode === "login" ? "register" : "login");
                }}
              >
                {mode === "login" ? "Regístrate" : "Inicia sesión"}
              </a>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
