import sys
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

from services.text_format import plain_chat_text
from ui.theme import COLORS, set_button_enabled, style_listbox

ROUTE_LABELS = {
    "sql": "Datos del taller",
    "rag": "Casos similares",
    "function_calling": "Consulta al sistema",
    "help": "Ayuda",
    "llm_direct": "Asistente",
    "error": "Error",
    "blocked": "Seguridad",
    "memory_recall": "Memoria",
}

STATUS_COLORS = {
    "thinking": "#93c5fd",
    "searching": "#fbbf24",
    "acting": "#34d399",
    "ready": "#94a3b8",
}

TYPEWRITER_MS = 16
TYPEWRITER_CHARS = 2
STREAM_CURSOR = "▌"


class TypewriterStream:
    """Revela texto de izquierda a derecha, estilo ChatGPT."""

    def __init__(self, window: tk.Misc, set_text: Callable[[str], None], scroll: Callable[[], None]):
        self._window = window
        self._set_text = set_text
        self._scroll = scroll
        self._target = ""
        self._shown = ""
        self._job: str | None = None
        self._streaming = False

    def append(self, chunk: str) -> None:
        if not chunk:
            return
        self._target += chunk
        if not self._streaming:
            self._streaming = True
            self._tick()

    def _tick(self) -> None:
        if len(self._shown) < len(self._target):
            backlog = len(self._target) - len(self._shown)
            step = TYPEWRITER_CHARS
            if backlog > 40:
                step = max(step, backlog // 4)
            elif backlog > 12:
                step = max(step, backlog // 6)
            self._shown = self._target[: len(self._shown) + step]
            self._set_text(self._shown + STREAM_CURSOR)
            self._scroll()
            self._job = self._window.after(TYPEWRITER_MS, self._tick)
            return

        if self._streaming:
            self._set_text(self._shown + STREAM_CURSOR)
            self._scroll()
            self._job = self._window.after(TYPEWRITER_MS, self._tick)

    def finish(self, final_text: str) -> str:
        if self._job:
            self._window.after_cancel(self._job)
            self._job = None
        self._target = final_text
        self._shown = final_text
        self._streaming = False
        self._set_text(final_text)
        self._scroll()
        return final_text

    @property
    def target(self) -> str:
        return self._target


class ChatWindow(tk.Toplevel):
    """Ventana flotante de chat con historial de conversaciones por usuario."""

    def __init__(self, master, chat_service):
        super().__init__(master)
        self.chat_service = chat_service
        self.title("Asistente IESPRO-Taller")
        self.geometry("780x640")
        self.minsize(640, 480)
        self.configure(bg=COLORS["chat_bg"])
        self._busy = False
        self._conv_ids: list[int] = []
        self._switching = False
        self._canvas_window_id: int | None = None
        self._chat_scroll_active = False
        self._chat_scroll_area: tk.Misc | None = None

        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self.chat_service.ensure_conversation()
        self._refresh_conversation_list()
        self._load_history()

    def _build_ui(self):
        header = tk.Frame(self, bg=COLORS["header"], height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Asistente del taller",
            bg=COLORS["header"],
            fg="white",
            font=("Helvetica", 15, "bold"),
        ).pack(anchor="w", padx=16, pady=(10, 0))

        self.status_var = tk.StringVar(value="Listo")
        self.status_label = tk.Label(
            header,
            textvariable=self.status_var,
            bg=COLORS["header"],
            fg=STATUS_COLORS["ready"],
            font=("Helvetica", 10),
        )
        self.status_label.pack(anchor="w", padx=16, pady=(0, 10))

        body = tk.Frame(self, bg=COLORS["chat_bg"])
        body.pack(fill="both", expand=True)

        # --- Sidebar ---
        sidebar = tk.Frame(body, bg="#1e293b", width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        side_head = tk.Frame(sidebar, bg="#1e293b", padx=10, pady=10)
        side_head.pack(fill="x")

        tk.Label(
            side_head,
            text="Conversaciones",
            bg="#1e293b",
            fg="#e2e8f0",
            font=("Helvetica", 10, "bold"),
        ).pack(side="left")

        self.new_btn = ttk.Button(
            side_head,
            text="+",
            style="Sidebar.TButton",
            command=self._new_conversation,
        )
        self.new_btn.pack(side="right")

        list_wrap = tk.Frame(sidebar, bg="#1e293b", padx=8, pady=8)
        list_wrap.pack(fill="both", expand=True)

        self.conv_listbox = tk.Listbox(
            list_wrap,
            activestyle="none",
            selectmode="browse",
            exportselection=False,
            bg="#0f172a",
            fg="#e2e8f0",
            selectbackground=COLORS["accent"],
            selectforeground="white",
            highlightthickness=0,
            borderwidth=0,
            font=("Helvetica", 10),
        )
        conv_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.conv_listbox.yview)
        self.conv_listbox.configure(yscrollcommand=conv_scroll.set)
        self.conv_listbox.pack(side="left", fill="both", expand=True)
        conv_scroll.pack(side="right", fill="y")
        style_listbox(self.conv_listbox)

        self.conv_listbox.bind("<<ListboxSelect>>", self._on_conversation_select)

        # --- Chat area ---
        chat_area = tk.Frame(body, bg=COLORS["chat_bg"])
        chat_area.pack(side="left", fill="both", expand=True)

        chat_wrap = tk.Frame(chat_area, bg=COLORS["chat_bg"])
        chat_wrap.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(chat_wrap, bg=COLORS["chat_bg"], highlightthickness=0)
        scroll = ttk.Scrollbar(chat_wrap, orient="vertical", command=self.canvas.yview)
        self.messages_frame = tk.Frame(self.canvas, bg=COLORS["chat_bg"])

        self._canvas_window_id = self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)

        self.messages_frame.bind("<Configure>", self._on_messages_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._chat_scroll_area = chat_wrap
        self.after_idle(self._activate_chat_scroll)

        bottom = tk.Frame(self, bg=COLORS["card"], padx=12, pady=12)
        bottom.pack(fill="x", side="bottom")

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            bottom,
            textvariable=self.input_var,
            font=("Helvetica", 12),
            relief="flat",
            bg="#f8fafc",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.input_entry.bind("<Return>", lambda e: self._send())

        self.voice_btn = ttk.Button(
            bottom,
            text="Voz",
            command=self._start_voice,
        )
        self.voice_btn.pack(side="right", padx=(0, 8))

        self.send_btn = ttk.Button(
            bottom,
            text="Enviar",
            style="Accent.TButton",
            command=self._send,
        )
        self.send_btn.pack(side="right")

        self.after(100, lambda: self.input_entry.focus_force())

    def _activate_chat_scroll(self, _event=None) -> None:
        if self._chat_scroll_active:
            return
        self._chat_scroll_active = True
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel, add="+")

    def _deactivate_chat_scroll(self, _event=None) -> None:
        if not self._chat_scroll_active:
            return
        self._chat_scroll_active = False
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _is_in_chat_scroll_area(self, widget: tk.Misc | None) -> bool:
        while widget is not None:
            if widget in (self.canvas, self.messages_frame, self._chat_scroll_area):
                return True
            if widget is self.conv_listbox:
                return False
            widget = widget.master
        return False

    def _bind_scroll_events(self, widget: tk.Misc) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_scroll_events(child)

    def _scroll_units(self, amount: int) -> None:
        if self.winfo_exists():
            self.canvas.yview_scroll(amount, "units")

    def _on_canvas_configure(self, event) -> None:
        if self._canvas_window_id is not None and event.width > 1:
            self.canvas.itemconfig(self._canvas_window_id, width=event.width)

    def _on_messages_frame_configure(self, _event=None) -> None:
        self._update_scroll_region()

    def _update_scroll_region(self) -> None:
        self.update_idletasks()
        canvas_width = max(self.canvas.winfo_width(), 1)
        frame_height = self.messages_frame.winfo_reqheight()
        if frame_height > 1:
            self.canvas.configure(scrollregion=(0, 0, canvas_width, frame_height))
            return
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)
        else:
            self.canvas.configure(scrollregion=(0, 0, canvas_width, 1))

    def _on_mousewheel(self, event):
        if not self.winfo_exists():
            return "break"

        try:
            px, py = self.winfo_pointerxy()
            widget = self.winfo_containing(px, py)
        except tk.TclError:
            widget = getattr(event, "widget", None)

        if not self._is_in_chat_scroll_area(widget):
            return

        if getattr(event, "num", None) == 4:
            self._scroll_units(-1)
            return "break"
        if getattr(event, "num", None) == 5:
            self._scroll_units(1)
            return "break"

        delta = getattr(event, "delta", 0)
        if not delta:
            return "break"

        if sys.platform == "darwin":
            step = int(-delta)
        elif abs(delta) >= 120:
            step = int(-delta / 120)
        else:
            step = int(-delta)

        if step == 0:
            step = -1 if delta > 0 else 1

        self.canvas.yview_scroll(step, "units")
        return "break"

    def _on_close(self):
        self._deactivate_chat_scroll()
        self.destroy()

    def _format_conv_label(self, conv: dict) -> str:
        titulo = (conv.get("titulo") or "Conversación").strip()
        if len(titulo) > 32:
            titulo = titulo[:29] + "..."
        return titulo

    def _refresh_conversation_list(self):
        if not hasattr(self, "conv_listbox"):
            return
        self._conv_ids = []
        self.conv_listbox.delete(0, tk.END)

        for conv in self.chat_service.list_conversations():
            self._conv_ids.append(conv["id"])
            self.conv_listbox.insert(tk.END, self._format_conv_label(conv))

        current = self.chat_service.id_conversacion
        if current in self._conv_ids:
            idx = self._conv_ids.index(current)
            self.conv_listbox.selection_clear(0, tk.END)
            self.conv_listbox.selection_set(idx)
            self.conv_listbox.see(idx)

    def _on_conversation_select(self, _event=None):
        if self._busy or self._switching:
            return

        sel = self.conv_listbox.curselection()
        if not sel:
            return

        idx = sel[0]
        if idx >= len(self._conv_ids):
            return

        conv_id = self._conv_ids[idx]
        if conv_id == self.chat_service.id_conversacion:
            return

        self._switching = True
        try:
            if self.chat_service.switch_conversation(conv_id):
                self._clear_messages()
                self._load_history()
                self._refresh_conversation_list()
        finally:
            self._switching = False

    def _clear_messages(self):
        for widget in self.messages_frame.winfo_children():
            widget.destroy()
        self._update_scroll_region()
        self._scroll_top()

    def _render_messages(self, messages: list[dict]):
        for msg in messages:
            role = msg.get("role")
            contenido = plain_chat_text(msg.get("contenido") or "")
            if not contenido.strip():
                continue
            if role == "user":
                self._user_message(contenido, scroll=False)
            elif role == "assistant":
                route = msg.get("route") or "llm_direct"
                label = ROUTE_LABELS.get(route, "Asistente")
                self._bot_message(contenido, meta=label, error=(route == "error"), scroll_to=None)

    def _load_history(self):
        messages = self.chat_service.get_ui_messages()
        if not messages:
            self._welcome()
            self._update_scroll_region()
            return
        self._render_messages(messages)
        self._update_scroll_region()
        self._scroll_bottom()

    def _new_conversation(self):
        if self._busy:
            return
        self.chat_service.start_new_conversation()
        self._clear_messages()
        self._welcome()
        self._refresh_conversation_list()

    def _welcome(self):
        self._bot_message(
            "Hola. Soy el asistente de IESPRO-Taller.\n\n"
            "Puedo consultar citas, vehículos, islas y mecánicos, "
            "o buscar fallas parecidas a las que ya atendimos.\n\n"
            "Escribe tu pregunta abajo y pulsa Enviar.",
            scroll_to="top",
        )

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        set_button_enabled(self.send_btn, not busy)
        set_button_enabled(self.new_btn, not busy)
        set_button_enabled(self.voice_btn, not busy)
        if not busy:
            self.input_entry.focus_force()

    def _set_agent_status(self, phase: str, label: str) -> None:
        self.status_var.set(label)
        self.status_label.configure(fg=STATUS_COLORS.get(phase, STATUS_COLORS["ready"]))

    def _start_voice(self):
        if self._busy:
            return

        self._set_busy(True)
        self._set_agent_status("thinking", "Escuchando micrófono...")

        def worker():
            from services.voice_service import transcribe_from_microphone

            ok, text = transcribe_from_microphone()
            self.after(0, lambda: self._finish_voice(ok, text))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_voice(self, ok: bool, text: str):
        if ok:
            self.input_var.set(text)
            self._set_agent_status("ready", "Voz transcrita. Revisa y envía.")
        else:
            self._set_agent_status("ready", text[:120])
        self._set_busy(False)

    def _send(self):
        if self._busy:
            return

        question = self.input_var.get().strip()
        if not question:
            return

        self.input_var.set("")
        self._user_message(question)
        self._set_busy(True)
        self._set_agent_status("thinking", "Pensando...")

        stream_msg = self._bot_message("", meta="Pensando...", scroll_to="bottom", streaming=True)
        typewriter = TypewriterStream(
            self,
            lambda text: self._set_stream_bubble_text(stream_msg, text),
            self._scroll_bottom,
        )

        def on_status(phase: str, label: str):
            self.after(0, lambda p=phase, l=label: self._update_stream_status(stream_msg, p, l))

        def on_token(chunk: str):
            self.after(0, lambda c=chunk: typewriter.append(c))

        def worker():
            try:
                result = self.chat_service.ask_stream(
                    question,
                    on_status=on_status,
                    on_token=on_token,
                )
                err = None
            except Exception as exc:
                result = None
                err = exc

            self.after(0, lambda: self._finish_send(stream_msg, result, err, typewriter))

        threading.Thread(target=worker, daemon=True).start()

    def _set_stream_bubble_text(self, stream_msg: dict, text: str) -> None:
        bubble = stream_msg.get("bubble_text")
        if bubble is None:
            return
        bubble.configure(state="normal")
        bubble.delete("1.0", "end")
        bubble.insert("1.0", text)
        bubble.configure(state="disabled")
        bubble.update_idletasks()
        line_count = int(bubble.index("end-1c").split(".")[0])
        bubble.configure(height=max(1, line_count))
        self._update_scroll_region()

    def _update_stream_status(self, stream_msg, phase: str, label: str):
        if stream_msg.get("meta_label"):
            stream_msg["meta_label"].configure(text=label)
        self._set_agent_status(phase, label)

    def _finish_send(self, stream_msg, result, err, typewriter: TypewriterStream):

        if err is not None:
            self._set_stream_bubble_text(stream_msg, f"No pude responder: {err}")
            if stream_msg.get("meta_label"):
                stream_msg["meta_label"].configure(text="Error")
            self._set_agent_status("ready", "Error al responder")
        else:
            route = result.get("route", "llm_direct")
            label = ROUTE_LABELS.get(route, "Asistente")
            answer = plain_chat_text(typewriter.target or result.get("answer", "") or "")
            if not answer.strip():
                answer = "No pude obtener una respuesta. Intenta de nuevo."
            typewriter.finish(answer)
            # Métricas de observabilidad (Semana 5): desactivadas en UI para demo limpia.
            # Los datos siguen guardándose en MySQL (llm_observability_logs).
            # Para volver a mostrarlas en cada respuesta, descomenta el bloque de abajo:
            # metrics = result.get("metrics") or {}
            meta = label
            # if metrics:
            #     meta = (
            #         f"{label} · TTFT {metrics.get('ttft_ms', '-')}ms · "
            #         f"Latencia {metrics.get('total_latency_ms', '-')}ms · "
            #         f"TPS {metrics.get('tokens_per_second', '-')}"
            #     )
            if stream_msg.get("meta_label"):
                stream_msg["meta_label"].configure(
                    text=meta,
                    fg=COLORS["muted"] if route != "error" else "#dc2626",
                )
            self._set_agent_status("ready", "Listo")

        self._refresh_conversation_list()
        self._set_busy(False)

    def _user_message(self, text, scroll=True):
        row = tk.Frame(self.messages_frame, bg=COLORS["chat_bg"])
        row.pack(fill="x", pady=6, padx=4)

        bubble = tk.Label(
            row,
            text=text,
            bg=COLORS["user_bubble"],
            fg=COLORS["user_text"],
            font=("Helvetica", 11),
            wraplength=380,
            justify="left",
            padx=14,
            pady=10,
        )
        bubble.pack(side="right", anchor="e")
        self._bind_scroll_events(row)
        if scroll:
            self._update_scroll_region()
            self._scroll_bottom()

    def _bot_message(self, text, meta=None, error=False, scroll_to="bottom", streaming=False):
        row = tk.Frame(self.messages_frame, bg=COLORS["chat_bg"])
        row.pack(fill="x", pady=6, padx=4)

        inner = tk.Frame(row, bg=COLORS["chat_bg"])
        inner.pack(side="left", anchor="w")

        if meta:
            meta_label = tk.Label(
                inner,
                text=meta,
                bg=COLORS["chat_bg"],
                fg=COLORS["muted"] if not error else "#dc2626",
                font=("Helvetica", 8, "bold"),
            )
            meta_label.pack(anchor="w", padx=4)
        else:
            meta_label = None

        bubble_bg = "#fee2e2" if error else COLORS["bot_bubble"]
        if streaming:
            bubble = tk.Text(
                inner,
                height=1,
                width=46,
                wrap="word",
                bg=bubble_bg,
                fg=COLORS["bot_text"],
                font=("Helvetica", 11),
                relief="flat",
                borderwidth=1,
                highlightthickness=1,
                highlightbackground=COLORS["border"],
                padx=10,
                pady=8,
                cursor="arrow",
            )
            bubble.pack(anchor="w")
            bubble.configure(state="normal")
            if text:
                bubble.insert("1.0", text)
            bubble.configure(state="disabled")

            def _resize(_event=None):
                bubble.update_idletasks()
                line_count = int(bubble.index("end-1c").split(".")[0])
                bubble.configure(height=max(1, line_count))

            bubble.bind("<Configure>", _resize)
            bubble_text = bubble
            bubble_label = None
        else:
            bubble_label = tk.Label(
                inner,
                text=text,
                bg=bubble_bg,
                fg=COLORS["bot_text"],
                font=("Helvetica", 11),
                wraplength=400,
                justify="left",
                padx=14,
                pady=10,
                relief="flat",
                borderwidth=1,
            )
            bubble_label.pack(anchor="w")
            bubble_text = None

        if scroll_to == "bottom":
            self._update_scroll_region()
            self._scroll_bottom()
        elif scroll_to == "top":
            self._update_scroll_region()
            self._scroll_top()
        self._bind_scroll_events(row)
        return {
            "row": row,
            "meta_label": meta_label,
            "bubble_label": bubble_label,
            "bubble_text": bubble_text,
        }

    def _scroll_top(self):
        self._update_scroll_region()
        self.canvas.yview_moveto(0.0)

    def _scroll_bottom(self):
        self._update_scroll_region()
        self.canvas.yview_moveto(1.0)
