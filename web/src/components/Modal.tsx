import type { ReactNode } from "react";

export function Modal({
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
      <div className="modal-backdrop" onClick={onClose} aria-hidden />
      <div
        className={`modal${wide ? " modal-wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <header className="modal-header">
          <h3 id="modal-title">{title}</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Cerrar">×</button>
        </header>
        <div className="modal-body">{children}</div>
        {footer && <footer className="modal-footer">{footer}</footer>}
      </div>
    </>
  );
}

export function ModalActions({
  onCancel,
  onSave,
  saveLabel = "Guardar",
  saving = false,
}: {
  onCancel: () => void;
  onSave: () => void;
  saveLabel?: string;
  saving?: boolean;
}) {
  return (
    <div className="modal-actions">
      <button type="button" className="btn-text" onClick={onCancel}>Cancelar</button>
      <button type="button" className="btn btn-save" onClick={onSave} disabled={saving}>
        {saveLabel}
      </button>
    </div>
  );
}
