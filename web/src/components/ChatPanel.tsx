import { useCallback, useEffect, useRef, useState } from "react";
import { api, ROUTE_LABELS, streamChat } from "../api/client";
import { useAuth, usePermissions } from "../context/AuthContext";
import { useSpeechInput } from "../hooks/useSpeechInput";
import { VoiceMicButton } from "./VoiceMicButton";

interface Conversation {
  id: number;
  titulo?: string;
  num_mensajes?: number;
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
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const messagesRequestRef = useRef(0);
  const activeConv = conversations.find((c) => c.id === activeId);
  const activeHasMessages =
    messages.length > 0 || (activeConv?.num_mensajes ?? 0) > 0;
  const canStartNewConversation =
    conversations.length === 0 || activeHasMessages;

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
    const requestId = ++messagesRequestRef.current;
    setLoadingMessages(true);
    try {
      const res = await api<{ messages: Array<{ role: string; contenido?: string; route?: string }> }>(
        `/api/chat/conversations/${id}/messages`,
        {},
        auth.token,
      );
      if (requestId !== messagesRequestRef.current) return;
      setMessages(
        res.messages.map((m) => ({
          role: m.role,
          content: m.contenido || "",
          route: m.route,
        })),
      );
    } finally {
      if (requestId === messagesRequestRef.current) setLoadingMessages(false);
    }
  }, [auth]);

  useEffect(() => {
    if (!auth?.user.id_sucursal || !perms.is_propietario) return;
    api("/api/rag/bootstrap", { method: "POST" }, auth.token).then(() => loadConversations());
  }, [auth, loadConversations, perms.is_propietario]);

  const staffReady = Boolean(auth?.user.id_sucursal && auth.user.id_isla);
  const canChat = perms.is_cliente
    ? Boolean(auth?.user.id_sucursal)
    : staffReady;

  useEffect(() => {
    if (activeId) loadMessages(activeId);
  }, [activeId, loadMessages]);

  useEffect(() => {
    scrollBottom();
  }, [messages]);

  const newConversation = async () => {
    if (!auth || !canStartNewConversation) return;
    setError("");
    const res = await api<{ ok: boolean; id: number }>(
      "/api/chat/conversations",
      { method: "POST" },
      auth.token,
    );
    setActiveId(res.id);
    setMessages([]);
    setInput("");
    await loadConversations();
    await api(`/api/chat/conversations/${res.id}/activate`, { method: "POST" }, auth.token);
  };

  const deleteConversation = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!auth) return;
    setError("");
    try {
      await api(`/api/chat/conversations/${id}`, { method: "DELETE" }, auth.token);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (activeId === id) {
        const nextId = remaining[0]?.id ?? null;
        setActiveId(nextId);
        setMessages([]);
        setInput("");
        if (nextId) {
          await api(`/api/chat/conversations/${nextId}/activate`, { method: "POST" }, auth.token);
          await loadMessages(nextId);
        }
      } else {
        await loadConversations();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo eliminar");
    }
  };

  const activate = async (id: number) => {
    if (!auth || id === activeId) return;
    setActiveId(id);
    await api(`/api/chat/conversations/${id}/activate`, { method: "POST" }, auth.token);
  };

  const submitMessage = useCallback(async (raw: string) => {
    if (!auth || !raw.trim() || sending) return;
    if (!activeId) {
      setError("Pulsa + Nueva conversación para empezar.");
      return;
    }
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
          onStatus: () => {},
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
    }
  }, [activeId, auth, loadConversations, sending]);

  const speech = useSpeechInput({
    disabled: false,
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
          <button
            type="button"
            className="btn btn-block"
            onClick={() => void newConversation()}
            disabled={!canStartNewConversation}
            title={
              canStartNewConversation
                ? conversations.length === 0
                  ? "Crear tu primera conversación"
                  : "Iniciar otra conversación"
                : "Escribe algo en esta conversación antes de abrir otra"
            }
          >
            + Nueva conversación
          </button>
          <div className="conv-list">
            {conversations.length === 0 && (
              <p className="conv-empty-hint">Sin conversaciones aún</p>
            )}
            {conversations.map((c) => (
              <div key={c.id} className="conv-item-row">
                <button
                  type="button"
                  className={`conv-item ${activeId === c.id ? "active" : ""}`}
                  onClick={() => activate(c.id)}
                >
                  {c.titulo || `Chat #${c.id}`}
                </button>
                <button
                  type="button"
                  className="conv-delete"
                  aria-label="Eliminar conversación"
                  title="Eliminar"
                  onClick={(e) => void deleteConversation(c.id, e)}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
        <div className="chat-main">
          <div className={`chat-messages${loadingMessages ? " is-loading" : ""}`}>
            {loadingMessages && (
              <p className="chat-messages-loading" aria-hidden>
                <span className="app-loader-spinner" />
              </p>
            )}
            {!loadingMessages && !activeId && conversations.length === 0 && (
              <p className="chat-welcome-hint">
                Pulsa <strong>+ Nueva conversación</strong> para empezar a chatear.
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`msg-row ${m.role === "user" ? "user" : "bot"}`}>
                <div className={`msg-bubble ${m.streaming ? "streaming" : ""}`}>
                  {m.content || (m.streaming ? "▍" : "")}
                  {m.route && !m.streaming && ROUTE_LABELS[m.route] && (
                    <div className="msg-route">{ROUTE_LABELS[m.route]}</div>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
          <form className="chat-compose" onSubmit={send}>
            <div className={`chat-compose-field${speech.voiceActive ? " voice-active" : ""}`}>
              <VoiceMicButton
                listening={speech.listening}
                disabled={false}
                onClick={speech.toggleListening}
                title={speech.listening ? "Detener y enviar" : "Hablar (envía al dejar de hablar)"}
              />
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Escribe tu pregunta o usa el micrófono…"
                className={speech.voiceActive ? "voice-active-input" : undefined}
              />
            </div>
            <button
              className="btn btn-send"
              type="submit"
              disabled={sending || !input.trim() || !activeId}
            >
              {sending ? "…" : "Enviar"}
            </button>
          </form>
          {speech.voiceError && <p className="error-text voice-error">{speech.voiceError}</p>}
        </div>
      </div>
    </div>
  );
}
