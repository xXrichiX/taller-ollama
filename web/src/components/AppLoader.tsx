interface AppLoaderProps {
  fullScreen?: boolean;
}

export function AppLoader({ fullScreen = true }: AppLoaderProps) {
  return (
    <div
      className={`app-loader${fullScreen ? " app-loader--fullscreen" : ""}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="Cargando"
    >
      <div className="app-loader-spinner" aria-hidden />
    </div>
  );
}
