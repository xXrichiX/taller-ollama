"""Estilos visuales IESPRO-Taller."""

import tkinter as tk
from tkinter import ttk

COLORS = {
    "bg": "#f1f5f9",
    "card": "#ffffff",
    "header": "#1e3a5f",
    "header_text": "#ffffff",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "text": "#1e293b",
    "muted": "#64748b",
    "border": "#cbd5e1",
    "user_bubble": "#2563eb",
    "user_text": "#ffffff",
    "bot_bubble": "#ffffff",
    "bot_text": "#1e293b",
    "chat_bg": "#e2e8f0",
}


def apply_theme(root):
    root.configure(bg=COLORS["bg"])

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=("Helvetica", 11))
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Header.TFrame", background=COLORS["header"])
    style.configure("Header.TLabel", background=COLORS["header"], foreground=COLORS["header_text"], font=("Helvetica", 13, "bold"))
    style.configure("SubHeader.TLabel", background=COLORS["header"], foreground="#cbd5e1", font=("Helvetica", 10))
    style.configure("TLabelframe", background=COLORS["bg"])
    style.configure("TLabelframe.Label", font=("Helvetica", 11, "bold"))
    style.configure("TNotebook.Tab", padding=(14, 8), font=("Helvetica", 10, "bold"))
    style.configure("Primary.TButton", font=("Helvetica", 11, "bold"), padding=(12, 6))
    style.configure("Treeview", rowheight=28, font=("Helvetica", 10))
    style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
    style.configure("Status.TLabel", background="#e2e8f0", foreground=COLORS["muted"], font=("Helvetica", 9))
    style.configure("Card.TFrame", background=COLORS["card"])
    style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"])
    style.configure("CardTitle.TLabel", background=COLORS["card"], foreground=COLORS["muted"], font=("Helvetica", 10))
    style.configure("CardValue.TLabel", background=COLORS["card"], foreground=COLORS["header"], font=("Helvetica", 22, "bold"))
    style.configure("CardAccent.TLabel", background=COLORS["card"], foreground=COLORS["accent"], font=("Helvetica", 22, "bold"))
    style.configure("Section.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Helvetica", 12, "bold"))

    _configure_action_buttons(style)
    _configure_header_combobox(style)


def _configure_header_combobox(style: ttk.Style) -> None:
    style.configure(
        "Header.TCombobox",
        fieldbackground="#2a4a72",
        background="#2a4a72",
        foreground="#ffffff",
        bordercolor="#4b6a94",
        lightcolor="#2a4a72",
        darkcolor="#1e3a5f",
        arrowcolor="#ffffff",
        padding=(10, 7),
    )
    style.map(
        "Header.TCombobox",
        fieldbackground=[("readonly", "#2a4a72"), ("disabled", "#334155")],
        foreground=[("readonly", "#ffffff"), ("disabled", "#94a3b8")],
        arrowcolor=[("disabled", "#94a3b8")],
    )


def _configure_action_buttons(style: ttk.Style) -> None:
    """Botones con color real (tk.Button en macOS suele verse blanco/opaco)."""
    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground="#ffffff",
        borderwidth=0,
        focusthickness=0,
        focuscolor=COLORS["accent"],
        font=("Helvetica", 11, "bold"),
        padding=(14, 8),
    )
    style.map(
        "Accent.TButton",
        background=[
            ("pressed", COLORS["accent_hover"]),
            ("active", COLORS["accent_hover"]),
            ("disabled", "#94a3b8"),
        ],
        foreground=[("disabled", "#ffffff")],
    )

    style.configure(
        "Sidebar.TButton",
        background="#334155",
        foreground="#ffffff",
        borderwidth=0,
        focusthickness=0,
        focuscolor="#334155",
        font=("Helvetica", 13, "bold"),
        padding=(6, 2),
        width=3,
    )
    style.map(
        "Sidebar.TButton",
        background=[
            ("pressed", COLORS["accent_hover"]),
            ("active", COLORS["accent"]),
            ("disabled", "#475569"),
        ],
        foreground=[("disabled", "#e2e8f0")],
    )

    style.configure(
        "ChatGhost.TButton",
        background=COLORS["card"],
        foreground=COLORS["text"],
        borderwidth=1,
        relief="flat",
        focusthickness=0,
        focuscolor=COLORS["card"],
        font=("Helvetica", 11, "bold"),
        padding=(12, 8),
    )
    style.map(
        "ChatGhost.TButton",
        background=[
            ("pressed", "#f1f5f9"),
            ("active", "#f8fafc"),
            ("disabled", "#f1f5f9"),
        ],
        foreground=[("disabled", COLORS["muted"])],
        bordercolor=[("active", COLORS["accent"]), ("!active", COLORS["border"])],
    )

    style.configure(
        "ChatScroll.TButton",
        background=COLORS["card"],
        foreground=COLORS["accent"],
        borderwidth=1,
        relief="flat",
        focusthickness=0,
        focuscolor=COLORS["card"],
        font=("Helvetica", 10, "bold"),
        padding=(10, 6),
    )
    style.map(
        "ChatScroll.TButton",
        background=[("pressed", "#eff6ff"), ("active", "#f8fafc")],
        foreground=[("disabled", COLORS["muted"])],
    )


def set_button_enabled(button: ttk.Button, enabled: bool) -> None:
    if enabled:
        button.state(["!disabled"])
    else:
        button.state(["disabled"])


def style_listbox(listbox: tk.Listbox) -> None:
    listbox.configure(
        bg=COLORS["card"],
        fg=COLORS["text"],
        selectbackground=COLORS["accent"],
        selectforeground=COLORS["user_text"],
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["accent"],
        relief="flat",
        borderwidth=1,
        font=("Helvetica", 10),
        activestyle="none",
    )


def style_text_widget(widget, *, height_bg: str | None = None) -> None:
    widget.configure(
        bg=height_bg or COLORS["card"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        relief="flat",
        borderwidth=1,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        font=("Helvetica", 11),
        padx=10,
        pady=10,
    )
