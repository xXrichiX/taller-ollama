"""Menú de perfil de usuario (avatar + desplegable)."""

import tkinter as tk
from typing import Callable

from ui.theme import COLORS

LOGOUT_RED = "#b91c1c"
MENU_WIDTH = 210


class UserProfileMenu(tk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        *,
        nombre: str,
        rol: str,
        on_profile: Callable[[], None],
        on_logout: Callable[[], None],
    ):
        super().__init__(master, bg=COLORS["header"])
        self.on_profile = on_profile
        self.on_logout = on_logout
        self._popup: tk.Toplevel | None = None
        self._outside_bind_id: str | None = None

        self._trigger = tk.Frame(self, bg=COLORS["header"], cursor="hand2")
        self._trigger.pack(anchor="w")
        for seq in ("<Button-1>",):
            self._trigger.bind(seq, self._toggle)

        avatar = tk.Canvas(self._trigger, width=46, height=46, bg=COLORS["header"], highlightthickness=0)
        avatar.pack(side="left", padx=(0, 12))
        avatar.create_oval(2, 2, 44, 44, fill="#e2e8f0", outline="#94a3b8", width=1)
        avatar.create_text(23, 23, text="👤", font=("Helvetica", 20))
        avatar.bind("<Button-1>", self._toggle)

        texts = tk.Frame(self._trigger, bg=COLORS["header"])
        texts.pack(side="left")

        name_row = tk.Frame(texts, bg=COLORS["header"])
        name_row.pack(anchor="w")
        name_lbl = tk.Label(
            name_row,
            text=nombre,
            bg=COLORS["header"],
            fg=COLORS["header_text"],
            font=("Helvetica", 14, "bold"),
        )
        name_lbl.pack(side="left")
        chevron = tk.Label(name_row, text="⌄", bg=COLORS["header"], fg=COLORS["header_text"], font=("Helvetica", 13))
        chevron.pack(side="left", padx=(6, 0))

        rol_lbl = tk.Label(
            texts,
            text=rol,
            bg=COLORS["header"],
            fg="#cbd5e1",
            font=("Helvetica", 10),
        )
        rol_lbl.pack(anchor="w", pady=(2, 0))

        for widget in (texts, name_row, name_lbl, chevron, rol_lbl):
            widget.bind("<Button-1>", self._toggle)

    def close_menu(self) -> None:
        self._close()

    def _toggle(self, _event=None) -> None:
        if self._popup and self._popup.winfo_exists():
            self._close()
        else:
            self._open()

    def _open(self) -> None:
        self._popup = tk.Toplevel(self)
        self._popup.overrideredirect(True)
        self._popup.configure(bg=COLORS["border"])
        self._popup.attributes("-topmost", True)

        x = self._trigger.winfo_rootx()
        y = self._trigger.winfo_rooty() + self._trigger.winfo_height() + 6
        self._popup.geometry(f"{MENU_WIDTH}x96+{x}+{y}")

        shell = tk.Frame(self._popup, bg=COLORS["border"], padx=1, pady=1)
        shell.pack(fill="both", expand=True)

        inner = tk.Frame(shell, bg=COLORS["card"])
        inner.pack(fill="both", expand=True)

        self._menu_item(inner, "👤   Mi Perfil", COLORS["text"], self._pick_profile)
        tk.Frame(inner, bg=COLORS["border"], height=1).pack(fill="x")
        self._menu_item(inner, "↪   Cerrar sesión", LOGOUT_RED, self._pick_logout)

        self.after(120, self._install_outside_bind)

    def _install_outside_bind(self) -> None:
        if not self._popup or not self._popup.winfo_exists():
            return
        root = self.winfo_toplevel()
        self._outside_bind_id = root.bind("<Button-1>", self._on_global_click, add="+")

    def _menu_item(self, parent: tk.Frame, text: str, fg: str, command: Callable[[], None]) -> None:
        row = tk.Label(
            parent,
            text=text,
            bg=COLORS["card"],
            fg=fg,
            anchor="w",
            font=("Helvetica", 11),
            padx=14,
            pady=11,
            cursor="hand2",
        )
        row.pack(fill="x")

        def activate(_e=None):
            command()

        row.bind("<Button-1>", activate)
        row.bind("<Enter>", lambda _e: row.configure(bg="#f1f5f9"))
        row.bind("<Leave>", lambda _e: row.configure(bg=COLORS["card"]))

    def _pick_profile(self) -> None:
        self._close()
        self.on_profile()

    def _pick_logout(self) -> None:
        self._close()
        self.after(10, self.on_logout)

    def _close(self) -> None:
        if self._outside_bind_id:
            try:
                self.winfo_toplevel().unbind("<Button-1>", self._outside_bind_id)
            except tk.TclError:
                pass
            self._outside_bind_id = None
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None

    def _on_global_click(self, event: tk.Event) -> None:
        if not self._popup or not self._popup.winfo_exists():
            self._close()
            return

        widget = event.widget
        inside = False
        current: tk.Misc | None = widget
        while current is not None:
            if current == self._popup or current == self._trigger:
                inside = True
                break
            try:
                current = current.master
            except (AttributeError, tk.TclError):
                break

        if not inside:
            self._close()
