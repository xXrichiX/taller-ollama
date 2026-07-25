import { ChatPanel } from "../components/ChatPanel";

export function ChatPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h2>Asistente IA</h2>
        <p className="muted">Historial, streaming y rutas del orquestador</p>
      </div>
      <ChatPanel />
    </div>
  );
}
