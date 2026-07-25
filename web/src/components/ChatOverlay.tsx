import { ChatPanel } from "./ChatPanel";

export function ChatOverlay({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <>
      <div className="overlay-backdrop" onClick={onClose} />
      <div className="chat-overlay" role="dialog" aria-modal="true">
        <header className="overlay-header">
          <div>
            <h2>Asistente IA</h2>
            <p className="muted">Multi-agente · RAG · Transaccional</p>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Cerrar">×</button>
        </header>
        <ChatPanel compact />
      </div>
    </>
  );
}
