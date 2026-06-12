import threading
import tkinter as tk
from tkinter import ttk

from services.text_format import plain_chat_text
from ui.theme import COLORS, style_listbox

ROUTE_LABELS = {
    "sql": "Datos del taller",
    "rag": "Casos similares",
    "function_calling": "Consulta al sistema",
    "help": "Ayuda",
    "llm_direct": "Asistente",
    "error": "Error",
}


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

        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self.chat_service.ensure_conversation()
        self._refresh_conversation_list()
        self._load_history()

    def _build_ui(self):
        header = tk.Frame(self, bg=COLORS["header"], height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="Asistente del taller",
            bg=COLORS["header"],
            fg="white",
            font=("Helvetica", 15, "bold"),
        ).pack(anchor="w", padx=16, pady=12)

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

        self.new_btn = tk.Button(
            side_head,
            text="+",
            width=2,
            height=1,
            bg="#334155",
            fg="white",
            activebackground=COLORS["accent"],
            activeforeground="white",
            relief="flat",
            font=("Helvetica", 14, "bold"),
            cursor="hand2",
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

        self.messages_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

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

        self.send_btn = tk.Button(
            bottom,
            text="Enviar",
            bg=COLORS["accent"],
            fg="white",
            activebackground=COLORS["accent_hover"],
            activeforeground="white",
            relief="flat",
            font=("Helvetica", 11, "bold"),
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._send,
        )
        self.send_btn.pack(side="right")

        self.after(100, lambda: self.input_entry.focus_force())

    def _on_mousewheel(self, event):
        if self.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_close(self):
        self.canvas.unbind("<MouseWheel>")
        self.canvas.unbind("<Button-4>")
        self.canvas.unbind("<Button-5>")
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
        finally:
            self._switching = False

    def _clear_messages(self):
        for widget in self.messages_frame.winfo_children():
            widget.destroy()

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
            return
        self._render_messages(messages)
        self._scroll_bottom()

    def _new_conversation(self):
        if self._busy:
            return
        self.chat_service.start_new_conversation()
        self._clear_messages()
        self._welcome()

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
        if busy:
            self.send_btn.configure(state="disabled", bg=COLORS["muted"])
            self.new_btn.configure(state="disabled")
        else:
            self.send_btn.configure(state="normal", bg=COLORS["accent"])
            self.new_btn.configure(state="normal")
            self.input_entry.focus_force()

    def _send(self):
        if self._busy:
            return

        question = self.input_var.get().strip()
        if not question:
            return

        self.input_var.set("")
        self._user_message(question)
        self._set_busy(True)

        thinking = self._bot_message("Un momento...", meta="Pensando")

        def worker():
            try:
                result = self.chat_service.ask(question)
                err = None
            except Exception as exc:
                result = None
                err = exc

            self.after(0, lambda: self._finish_send(thinking, result, err))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_send(self, thinking, result, err):
        thinking.destroy()

        if err is not None:
            self._bot_message(f"No pude responder: {err}", meta="Error", error=True)
        else:
            route = result.get("route", "llm_direct")
            label = ROUTE_LABELS.get(route, "Asistente")
            answer = plain_chat_text(result.get("answer", "") or "")
            if not answer.strip():
                answer = "No pude obtener una respuesta. Intenta de nuevo."
            self._bot_message(answer, meta=label, error=(route == "error"))

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
        if scroll:
            self._scroll_bottom()

    def _bot_message(self, text, meta=None, error=False, scroll_to="bottom"):
        row = tk.Frame(self.messages_frame, bg=COLORS["chat_bg"])
        row.pack(fill="x", pady=6, padx=4)

        inner = tk.Frame(row, bg=COLORS["chat_bg"])
        inner.pack(side="left", anchor="w")

        if meta:
            tk.Label(
                inner,
                text=meta,
                bg=COLORS["chat_bg"],
                fg=COLORS["muted"] if not error else "#dc2626",
                font=("Helvetica", 8, "bold"),
            ).pack(anchor="w", padx=4)

        bubble = tk.Label(
            inner,
            text=text,
            bg="#fee2e2" if error else COLORS["bot_bubble"],
            fg=COLORS["bot_text"],
            font=("Helvetica", 11),
            wraplength=400,
            justify="left",
            padx=14,
            pady=10,
            relief="flat",
            borderwidth=1,
        )
        bubble.pack(anchor="w")
        if scroll_to == "bottom":
            self._scroll_bottom()
        elif scroll_to == "top":
            self._scroll_top()
        return row

    def _scroll_top(self):
        self.update_idletasks()
        self.canvas.yview_moveto(0.0)

    def _scroll_bottom(self):
        self.update_idletasks()
        self.canvas.yview_moveto(1.0)
