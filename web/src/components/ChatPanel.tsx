import { useCallback, useEffect, useRef, useState } from "react";
import { api, ROUTE_LABELS, streamChat } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { useSpeechInput } from "../hooks/useSpeechInput";
import { VoiceMicButton } from "./VoiceMicButton";

interface Conversation {
  id: number;
  titulo?: string;
}

interface Message {
  role: string;
  content: string;
  route?: string;
  streaming?: boolean;
}

export function ChatPanel({ compact }: { compact?: boolean }) {
  const { auth } = useAuth();
  const perms = usePermissions();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadConversations = useCallback(async () => {
    if (!auth) return;
    const res = await api<{ conversations: Conversation[] }>("/api/chat/conversations", {}, auth.token);
    setConversations(res.conversations);
    if (res.conversations.length && !activeId) setActiveId(res.conversations[0].id);
  }, [auth, activeId]);

  const loadMessages = useCallback(async (id: number) => {
    if (!auth) return;
    const res = await api<{ messages: Array<{ role: string; contenido?: string; route?: string }> }>(
      `/api/chat/conversations/${id}/messages`,
      {},
      auth.token,
    );
    setMessages(
      res.messages.map((m) => ({
        role: m.role,
        content: m.contenido || "",
        route: m.route,
      })),
    );
  }, [auth]);

  useEffect(() => {
    if (!auth?.user.id_sucursal) return;
    api("/api/rag/bootstrap", { method: "POST" }, auth.token).then(() => loadConversations());
  }, [auth, loadConversations]);

  const staffReady = Boolean(auth?.user.id_sucursal && auth.user.id_isla);
  const canChat = perms.is_cliente
    ? Boolean(auth?.user.id_sucursal)
    : staffReady;

  useEffect(() => {
    if (activeId) loadMessages(activeId);
  }, [activeId, loadMessages]);

  useEffect(() => {
    scrollBottom();
  }, [messages, status]);

  const newConversation = async () => {
    if (!auth) return;
    await api("/api/chat/conversations", { method: "POST" }, auth.token);
    await loadConversations();
  };

  const activate = async (id: number) => {
    if (!auth) return;
    await api(`/api/chat/conversations/${id}/activate`, { method: "POST" }, auth.token);
    setActiveId(id);
  };

  const submitMessage = useCallback(async (raw: string) => {
    if (!auth || !raw.trim() || sending) return;
    setError("");
    setSending(true);
    const text = raw.trim();
    setInput("");
    setMessages((m) => [
      ...m,
      { role: "user", content: text },
      { role: "assistant", content: "", streaming: true },
    ]);

    try {
      await streamChat(
        text,
        auth.user.id_sucursal,
        {
          onStatus: (label) => setStatus(label),
          onToken: (chunk) => {
            setMessages((prev) => {
              const copy = [...prev];
              for (let i = copy.length - 1; i >= 0; i -= 1) {
                if (copy[i].role === "assistant" && copy[i].streaming) {
                  copy[i] = { ...copy[i], content: copy[i].content + chunk };
                  break;
                }
              }
              return copy;
            });
          },
          onDone: (data) => {
            setMessages((prev) => {
              const copy = [...prev];
              const last = copy[copy.length - 1];
              if (last?.role === "assistant") {
                copy[copy.length - 1] = {
                  role: "assistant",
                  content: last.content || data.answer || "",
                  route: data.route,
                };
              }
              return copy;
            });
            setStatus("");
            loadConversations();
          },
          onError: (msg) => setError(msg),
        },
        auth.token,
        auth.user.id_isla,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
      setMessages((m) => m.filter((x) => !x.streaming));
    } finally {
      setSending(false);
      setStatus("");
    }
  }, [auth, loadConversations, sending]);

  const speech = useSpeechInput({
    disabled: sending,
    authToken: auth?.token,
    onTranscript: setInput,
    onAutoSend: (text) => {
      void submitMessage(text);
    },
  });

  const send = (e: React.FormEvent) => {
    e.preventDefault();
    void submitMessage(input);
  };

  if (!canChat) {
    return (
      <div className="alert warn">
        {perms.is_cliente
          ? "Selecciona una sucursal para usar el asistente."
          : "Selecciona una isla en la barra azul para usar el asistente."}
      </div>
    );
  }

  return (
    <div className={`chat-shell ${compact ? "compact" : ""}`}>
      {error && <p className="error-text">{error}</p>}
      <div className="chat-layout">
        <div className="chat-sidebar">
          <button type="button" className="btn btn-block" onClick={newConversation}>+ Nueva conversación</button>
          <div className="conv-list">
            {conversations.map((c) => (
              <button
                key={c.id}
                type="button"
                className={`conv-item ${activeId === c.id ? "active" : ""}`}
                onClick={() => activate(c.id)}
              >
                {c.titulo || `Chat #${c.id}`}
              </button>
            ))}
          </div>
        </div>
        <div className="chat-main">
          <div className="chat-messages">
            {messages.length === 0 && (
              <div className="chat-empty">
                <p>Hola, soy el asistente de IESPRO-Taller.</p>
                <p className="muted">Pregunta sobre citas, vehículos o fallas comunes.</p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`msg-row ${m.role === "user" ? "user" : "bot"}`}>
                <div className={`msg-bubble ${m.streaming ? "streaming" : ""}`}>
                  {m.content || (m.streaming ? "▍" : "")}
                  {m.route && !m.streaming && (
                    <div className="msg-route">{ROUTE_LABELS[m.route] || m.route}</div>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          {status && (
            <div className="chat-status">
              <span className="pulse-dot" />
              {status}
            </div>
          )}
          <form className="chat-compose" onSubmit={send}>
            <div className={`chat-compose-field${speech.listening ? " voice-active" : ""}`}>
              <VoiceMicButton
                listening={speech.listening}
                disabled={sending}
                onClick={speech.toggleListening}
                title={
                  speech.listening
                    ? "Detener y enviar"
                    : "Hablar (envía tras 2 s de silencio)"
                }
              />
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  speech.listening
                    ? input.trim()
                      ? ""
                      : "Habla ahora…"
                    : "Escribe tu pregunta o usa el micrófono…"
                }
                disabled={sending}
                className={speech.listening ? "voice-active-input" : undefined}
              />
            </div>
            <button className="btn btn-send" type="submit" disabled={sending || !input.trim()}>
              {sending ? "…" : "Enviar"}
            </button>
          </form>
          {speech.listening && (
            <p className="voice-hint">
              <span className="pulse-dot" />
              Escuchando — se enviará automáticamente tras {speech.silenceSeconds} s de silencio
            </p>
          )}
          {speech.voiceError && <p className="error-text voice-error">{speech.voiceError}</p>}
        </div>
      </div>
    </div>
  );
}
