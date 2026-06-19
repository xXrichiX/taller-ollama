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
COMPOSE_BTN = 32


class RoundMicButton(tk.Canvas):
    """Botón circular de micrófono con animación de ondas al escuchar."""

    def __init__(self, master, command: Callable[[], None] | None = None, *, bg: str = "#ffffff"):
        self._size = COMPOSE_BTN
        super().__init__(
            master,
            width=self._size,
            height=self._size,
            highlightthickness=0,
            bg=bg,
            cursor="hand2",
        )
        self._command = command
        self._enabled = True
        self._listening = False
        self._anim_job: str | None = None
        self._anim_tick = 0
        self.bind("<Button-1>", self._on_click)
        self.draw_idle()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        if self._listening and not enabled:
            self.stop_listening()
        elif not self._listening:
            self.draw_idle()

    def _draw_mic_icon(self, cx: int, cy: int, color: str, *, scale: float = 1.0) -> None:
        w = max(1, int(1.5 * scale))
        body_w = int(4 * scale)
        body_h = int(7 * scale)
        top = int(cy - 8 * scale)
        bottom = top + body_h
        left = int(cx - body_w / 2)
        right = int(cx + body_w / 2)
        self.create_oval(left, top, right, top + body_w, fill=color, outline=color)
        self.create_rectangle(left, top + body_w // 2, right, bottom, fill=color, outline=color)
        self.create_arc(
            int(cx - 6 * scale),
            int(cy - 4 * scale),
            int(cx + 6 * scale),
            int(cy + 6 * scale),
            start=0,
            extent=180,
            style="arc",
            width=w,
            outline=color,
        )
        stem_y = int(cy + 8 * scale)
        self.create_line(cx, int(cy + 5 * scale), cx, stem_y, fill=color, width=w, capstyle="round")
        self.create_line(
            int(cx - 4 * scale),
            stem_y,
            int(cx + 4 * scale),
            stem_y,
            fill=color,
            width=w,
            capstyle="round",
        )

    def draw_idle(self) -> None:
        self.delete("all")
        s = self._size
        pad = 1
        fill = COLORS["accent"] if self._enabled else "#94a3b8"
        self.create_oval(pad, pad, s - pad, s - pad, fill=fill, outline="")
        self._draw_mic_icon(s // 2, s // 2 + 1, "white", scale=0.88)

    def start_listening(self) -> None:
        self._listening = True
        self._anim_tick = 0
        self._animate()

    def stop_listening(self) -> None:
        self._listening = False
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None
        self.draw_idle()

    def _animate(self) -> None:
        if not self._listening:
            return
        self._anim_tick += 1
        self.delete("all")
        s = self._size
        cx = cy = s // 2
        pulse = 14 + (self._anim_tick % 4)
        self.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, fill="#dbeafe", outline="")
        self.create_oval(1, 1, s - 1, s - 1, fill=COLORS["accent"], outline="")
        self._draw_mic_icon(cx, cy + 1, "white", scale=0.88)
        self._anim_job = self.after(140, self._animate)

    def _on_click(self, _event=None) -> None:
        if self._enabled and self._command:
            self._command()


class RoundStopButton(tk.Canvas):
    """Botón cuadrado rojo con icono de stop (detener grabación)."""

    def __init__(self, master, command: Callable[[], None] | None = None, *, bg: str = "#ffffff"):
        self._size = COMPOSE_BTN
        super().__init__(
            master,
            width=self._size,
            height=self._size,
            highlightthickness=0,
            bg=bg,
            cursor="hand2",
        )
        self._command = command
        self._enabled = True
        self.bind("<Button-1>", self._on_click)
        self.draw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        s = self._size
        pad = 2
        fill = "#ef4444" if self._enabled else "#fca5a5"
        self.create_rectangle(pad, pad, s - pad, s - pad, fill=fill, outline="")
        inner = 9
        cx = cy = s // 2
        self.create_rectangle(
            cx - inner // 2,
            cy - inner // 2,
            cx + inner // 2,
            cy + inner // 2,
            fill="white",
            outline="white",
        )

    def _on_click(self, _event=None) -> None:
        if self._enabled and self._command:
            self._command()


class RoundSendButton(tk.Canvas):
    """Botón circular azul con flecha de enviar."""

    def __init__(self, master, command: Callable[[], None] | None = None, *, bg: str = "#ffffff"):
        self._size = COMPOSE_BTN
        super().__init__(
            master,
            width=self._size,
            height=self._size,
            highlightthickness=0,
            bg=bg,
            cursor="hand2",
        )
        self._command = command
        self._enabled = True
        self.bind("<Button-1>", self._on_click)
        self.draw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        s = self._size
        fill = COLORS["accent"] if self._enabled else "#94a3b8"
        cx = cy = s // 2
        self.create_oval(1, 1, s - 1, s - 1, fill=fill, outline="")
        self.create_line(cx, cy + 4, cx, cy - 4, fill="white", width=2, capstyle="round")
        self.create_polygon(
            cx - 4,
            cy - 1,
            cx + 4,
            cy - 1,
            cx,
            cy - 7,
            fill="white",
            outline="white",
        )

    def _on_click(self, _event=None) -> None:
        if self._enabled and self._command:
            self._command()


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
        self._voice_active = False
        self._voice_session = None
        self._conv_ids: list[int] = []
        self._switching = False
        self._canvas_window_id: int | None = None
        self._chat_scroll_active = False
        self._chat_scroll_area: tk.Misc | None = None
        self._stick_to_bottom = True

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
        self._chat_scrollbar = ttk.Scrollbar(chat_wrap, orient="vertical", command=self._on_scrollbar_drag)
        self.messages_frame = tk.Frame(self.canvas, bg=COLORS["chat_bg"])

        self._canvas_window_id = self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_canvas_yview)

        self.messages_frame.bind("<Configure>", self._on_messages_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self._chat_scrollbar.pack(side="right", fill="y")

        self._chat_scroll_area = chat_wrap
        self.after_idle(self._activate_chat_scroll)

        bottom_outer = tk.Frame(self, bg=COLORS["chat_bg"])
        bottom_outer.pack(fill="x", side="bottom")

        tk.Frame(bottom_outer, bg="#cbd5e1", height=1).pack(fill="x")

        bottom = tk.Frame(bottom_outer, bg=COLORS["chat_bg"], padx=28, pady=10)
        bottom.pack(fill="x")

        compose = tk.Frame(
            bottom,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#d1d5db",
            highlightcolor=COLORS["accent"],
        )
        compose.pack(fill="x")

        input_row = tk.Frame(compose, bg="#ffffff")
        input_row.pack(fill="x", padx=6, pady=5)

        self._input_placeholder = "Mensaje..."
        self._placeholder_active = False
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_row,
            textvariable=self.input_var,
            font=("Helvetica", 11),
            relief="flat",
            bd=0,
            bg="#ffffff",
            fg=COLORS["text"],
            insertbackground=COLORS["accent"],
            highlightthickness=0,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=4)
        self.input_entry.bind("<Return>", lambda e: self._send())
        self.input_entry.bind("<FocusIn>", self._on_input_focus_in)
        self.input_entry.bind("<FocusOut>", self._on_input_focus_out)
        self.input_var.trace_add("write", self._on_input_changed)

        self.action_slot = tk.Frame(input_row, bg="#ffffff", width=COMPOSE_BTN, height=COMPOSE_BTN)
        self.action_slot.pack(side="right", padx=(0, 2))
        self.action_slot.pack_propagate(False)

        self.mic_btn = RoundMicButton(self.action_slot, command=self._start_voice, bg="#ffffff")
        self.mic_btn.pack()

        self.stop_btn = RoundStopButton(self.action_slot, command=self._stop_voice, bg="#ffffff")

        self.send_btn = RoundSendButton(self.action_slot, command=self._send, bg="#ffffff")

        self._show_input_placeholder()
        self._update_compose_actions()

        self.after(100, lambda: self.input_entry.focus_force())

    def _on_input_changed(self, *_args) -> None:
        if self._placeholder_active:
            return
        self.after_idle(self._update_compose_actions)

    def _update_compose_actions(self) -> None:
        if not hasattr(self, "mic_btn"):
            return
        if self._voice_active:
            self.mic_btn.pack_forget()
            self.send_btn.pack_forget()
            self.stop_btn.pack()
            return
        self.stop_btn.pack_forget()
        has_text = bool(self._get_input_text())
        if has_text:
            self.mic_btn.pack_forget()
            self.send_btn.pack()
        else:
            self.send_btn.pack_forget()
            self.mic_btn.pack()

    def _set_compose_enabled(self, enabled: bool) -> None:
        self.mic_btn.set_enabled(enabled)
        self.send_btn.set_enabled(enabled)
        if hasattr(self, "stop_btn") and not self._voice_active:
            self.stop_btn.set_enabled(enabled)

    def _show_input_placeholder(self) -> None:
        if self.input_var.get().strip():
            return
        self._placeholder_active = True
        self.input_var.set(self._input_placeholder)
        self.input_entry.configure(fg=COLORS["muted"])

    def _on_input_focus_in(self, _event=None) -> None:
        if self._placeholder_active:
            self.input_var.set("")
            self.input_entry.configure(fg=COLORS["text"])
            self._placeholder_active = False

    def _on_input_focus_out(self, _event=None) -> None:
        if not self.input_var.get().strip():
            self._show_input_placeholder()
        self._update_compose_actions()

    def _get_input_text(self) -> str:
        text = self.input_var.get().strip()
        if self._placeholder_active or text == self._input_placeholder:
            return ""
        return text

    def _on_canvas_yview(self, first: str, last: str) -> None:
        self._chat_scrollbar.set(first, last)
        self.after_idle(self._sync_stick_to_bottom)

    def _on_scrollbar_drag(self, *args) -> None:
        self.canvas.yview(*args)
        self.after_idle(self._sync_stick_to_bottom)

    def _is_near_bottom(self, threshold: float = 0.05) -> bool:
        try:
            _top, bottom = self.canvas.yview()
        except tk.TclError:
            return True
        return bottom >= (1.0 - threshold)

    def _sync_stick_to_bottom(self) -> None:
        if not self.winfo_exists():
            return
        if self._is_near_bottom():
            self._stick_to_bottom = True
        else:
            self._stick_to_bottom = False

    def _scroll_bottom_if_sticky(self) -> None:
        if self._stick_to_bottom:
            self._scroll_bottom(force=True)

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
            if amount < 0:
                self._stick_to_bottom = False
            self.after_idle(self._sync_stick_to_bottom)

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
        if self._voice_active and self._voice_session:
            self._voice_active = False
            self._voice_session.stop()
            self._voice_session = None
        self.mic_btn.stop_listening()
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
        self._stick_to_bottom = True
        self._update_scroll_region()
        self._scroll_top(force=True)

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
        self._stick_to_bottom = True
        messages = self.chat_service.get_ui_messages()
        if not messages:
            self._welcome()
            self._update_scroll_region()
            return
        self._render_messages(messages)
        self._update_scroll_region()
        self._scroll_bottom(force=True)

    def _new_conversation(self):
        if self._busy or self._voice_active:
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
        set_button_enabled(self.new_btn, not busy and not self._voice_active)
        if not self._voice_active:
            self._set_compose_enabled(not busy)
        elif hasattr(self, "stop_btn"):
            self.stop_btn.set_enabled(True)
        if not busy:
            self.input_entry.focus_force()
            if not self.input_var.get().strip():
                self._show_input_placeholder()
            self._update_compose_actions()

    def _set_agent_status(self, phase: str, label: str) -> None:
        self.status_var.set(label)
        self.status_label.configure(fg=STATUS_COLORS.get(phase, STATUS_COLORS["ready"]))

    def _start_voice(self):
        if self._busy or self._voice_active:
            return

        self._voice_active = True
        self._placeholder_active = False
        if self.input_var.get().strip() in ("", self._input_placeholder):
            self.input_var.set("")
        self.input_entry.configure(fg=COLORS["text"])
        self._update_compose_actions()
        self._set_agent_status("thinking", "Preparando reconocimiento de voz...")

        from services.voice_service import RealtimeVoiceSession

        self._voice_session = RealtimeVoiceSession(
            on_partial=lambda text: self.after(0, lambda t=text: self._apply_voice_partial(t)),
            on_error=lambda msg: self.after(0, lambda m=msg: self._handle_voice_error(m)),
            on_ready=lambda: self.after(
                0,
                lambda: self._set_agent_status("thinking", "Escuchando... habla ahora"),
            ),
        )
        self._voice_session.start()

    def _apply_voice_partial(self, text: str) -> None:
        if not self._voice_active or not text:
            return
        self._placeholder_active = False
        self.input_var.set(text)
        self.input_entry.configure(fg=COLORS["text"])

    def _stop_voice(self) -> None:
        if not self._voice_active:
            return

        self._voice_active = False
        session = self._voice_session
        self._voice_session = None

        transcript = session.stop() if session else ""
        final = (transcript or self._get_input_text()).strip()

        if final:
            self._placeholder_active = False
            self.input_var.set(final)
            self.input_entry.configure(fg=COLORS["text"])
            self._set_agent_status("ready", "Voz transcrita. Revisa y envía.")
        else:
            self._set_agent_status("ready", "Listo")
            if not self.input_var.get().strip():
                self._show_input_placeholder()

        self._update_compose_actions()
        self.input_entry.focus_force()

    def _handle_voice_error(self, msg: str) -> None:
        partial = self._get_input_text()
        if self._voice_active:
            self._voice_active = False
            if self._voice_session:
                self._voice_session.stop()
                self._voice_session = None

        if partial:
            self._placeholder_active = False
            self.input_var.set(partial)
            self.input_entry.configure(fg=COLORS["text"])
            self._set_agent_status("ready", "Texto parcial conservado.")
        else:
            self._set_agent_status("ready", msg[:120])
            if not self.input_var.get().strip():
                self._show_input_placeholder()

        self._update_compose_actions()

    def _send(self):
        if self._busy:
            return

        question = self._get_input_text()
        if not question:
            return

        self.input_var.set("")
        self._placeholder_active = False
        self.input_entry.configure(fg=COLORS["text"])
        self._stick_to_bottom = True
        self._update_compose_actions()
        self._user_message(question)
        self._set_busy(True)
        self._set_agent_status("thinking", "Pensando...")

        stream_msg = self._bot_message("", meta="Pensando...", scroll_to="bottom", streaming=True)
        typewriter = TypewriterStream(
            self,
            lambda text: self._set_stream_bubble_text(stream_msg, text),
            self._scroll_bottom_if_sticky,
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
        self._scroll_bottom_if_sticky()

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
        self._scroll_bottom_if_sticky()
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
            self._scroll_bottom(force=True)

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
            self._scroll_bottom(force=True)
        elif scroll_to == "top":
            self._update_scroll_region()
            self._scroll_top(force=True)
        self._bind_scroll_events(row)
        return {
            "row": row,
            "meta_label": meta_label,
            "bubble_label": bubble_label,
            "bubble_text": bubble_text,
        }

    def _scroll_top(self, force: bool = False) -> None:
        self._update_scroll_region()
        self.canvas.yview_moveto(0.0)
        if force:
            self._stick_to_bottom = False
            self.after_idle(self._sync_stick_to_bottom)

    def _scroll_bottom(self, force: bool = False) -> None:
        if not force and not self._stick_to_bottom:
            return
        self._update_scroll_region()
        self.canvas.yview_moveto(1.0)
        if force:
            self._stick_to_bottom = True
