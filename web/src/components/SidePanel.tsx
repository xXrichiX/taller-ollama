import type { ReactNode } from "react";

export function SidePanel({
  open,
  title,
  onClose,
  children,
  footer,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}) {
  if (!open) return null;
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} aria-hidden />
      <aside className={`drawer${wide ? " drawer-wide" : ""}`} role="dialog" aria-modal="true">
        <header className="drawer-header">
          <h3>{title}</h3>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Cerrar">×</button>
        </header>
        <div className="drawer-body">{children}</div>
        {footer && <footer className="drawer-footer">{footer}</footer>}
      </aside>
    </>
  );
}
