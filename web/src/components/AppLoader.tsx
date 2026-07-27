interface AppLoaderProps {
  message?: string;
  fullScreen?: boolean;
}

export function AppLoader({
  message = "Cargando…",
  fullScreen = true,
}: AppLoaderProps) {
  return (
    <div
      className={`app-loader${fullScreen ? " app-loader--fullscreen" : ""}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="app-loader-card">
        <div className="app-loader-mark" aria-hidden>
          <span className="app-loader-mark-inner" />
        </div>
        <p className="app-loader-brand">IESPRO-Taller</p>
        <div className="app-loader-spinner" aria-hidden />
        <p className="app-loader-message">{message}</p>
      </div>
    </div>
  );
}
