import threading
import tkinter as tk
from tkinter import ttk

from services.text_format import plain_chat_text
from ui.theme import COLORS

ROUTE_LABELS = {
    "sql": "Datos del taller",
    "rag": "Casos similares",
    "function_calling": "Consulta al sistema",
    "help": "Ayuda",
    "llm_direct": "Asistente",
    "error": "Error",
}


class ChatWindow(tk.Toplevel):
    """Ventana flotante de chat — estilo conversación, sin JSON crudo."""

    def __init__(self, master, chat_service):
        super().__init__(master)
        self.chat_service = chat_service
        self.title("Asistente IESPRO-Taller")
        self.geometry("520x640")
        self.minsize(420, 480)
        self.configure(bg=COLORS["chat_bg"])
        self._busy = False

        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._load_history()

    def _build_ui(self):
        header = tk.Frame(self, bg=COLORS["header"], height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_row = tk.Frame(header, bg=COLORS["header"])
        title_row.pack(fill="x", padx=16, pady=(10, 0))

        tk.Label(
            title_row,
            text="Asistente del taller",
            bg=COLORS["header"],
            fg="white",
            font=("Helvetica", 15, "bold"),
        ).pack(side="left")

        new_btn = tk.Button(
            title_row,
            text="Nueva conversación",
            bg="#334155",
            fg="white",
            activebackground="#475569",
            activeforeground="white",
            relief="flat",
            font=("Helvetica", 9),
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._new_conversation,
        )
        new_btn.pack(side="right")

        tk.Label(
            header,
            text="Pregunta sobre citas, fallas, islas o vehículos",
            bg=COLORS["header"],
            fg="#94a3b8",
            font=("Helvetica", 10),
        ).pack(anchor="w", padx=16, pady=(2, 8))

        chat_wrap = tk.Frame(self, bg=COLORS["chat_bg"])
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

    def _clear_messages(self):
        for widget in self.messages_frame.winfo_children():
            widget.destroy()

    def _load_history(self):
        self.chat_service.ensure_conversation()
        messages = self.chat_service.get_ui_messages()

        if not messages:
            self._welcome()
            return

        for msg in messages:
            role = msg.get("role")
            contenido = plain_chat_text(msg.get("contenido") or "")
            if not contenido.strip():
                continue
            if role == "user":
                self._user_message(contenido)
            elif role == "assistant":
                route = msg.get("route") or "llm_direct"
                label = ROUTE_LABELS.get(route, "Asistente")
                error = route == "error"
                self._bot_message(contenido, meta=label, error=error)

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
        )

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self.send_btn.configure(state="disabled", bg=COLORS["muted"])
        else:
            self.send_btn.configure(state="normal", bg=COLORS["accent"])
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

        self._set_busy(False)

    def _user_message(self, text):
        row = tk.Frame(self.messages_frame, bg=COLORS["chat_bg"])
        row.pack(fill="x", pady=6, padx=4)

        bubble = tk.Label(
            row,
            text=text,
            bg=COLORS["user_bubble"],
            fg=COLORS["user_text"],
            font=("Helvetica", 11),
            wraplength=340,
            justify="left",
            padx=14,
            pady=10,
        )
        bubble.pack(side="right", anchor="e")
        self._scroll_bottom()

    def _bot_message(self, text, meta=None, error=False):
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
            wraplength=360,
            justify="left",
            padx=14,
            pady=10,
            relief="flat",
            borderwidth=1,
        )
        bubble.pack(anchor="w")
        self._scroll_bottom()
        return row

    def _scroll_bottom(self):
        self.update_idletasks()
        self.canvas.yview_moveto(1.0)
