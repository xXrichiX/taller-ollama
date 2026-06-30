"""Campo de contraseña con icono para mostrar/ocultar."""

import tkinter as tk
from tkinter import ttk

from config import BASE_DIR
from ui.theme import COLORS

_ICON_SIZE = 16
_SUBSAMPLE = 32  # 512px → 16px


class PasswordField(ttk.Frame):
    _icons: dict[str, tk.PhotoImage] = {}

    def __init__(self, master, textvariable: tk.StringVar, *, width: int = 38):
        super().__init__(master)
        self._visible = False
        self._ensure_icons(master)

        self.entry = ttk.Entry(self, textvariable=textvariable, show="•", width=width)
        self.entry.pack(side="left", fill="x", expand=True)

        self._toggle = tk.Label(
            self,
            image=self._icons["hide"],
            cursor="hand2",
            bg=COLORS["bg"],
        )
        self._toggle.pack(side="right", padx=(6, 0))
        self._toggle.bind("<Button-1>", lambda _e: self._toggle_visibility())

    @classmethod
    def _ensure_icons(cls, master: tk.Misc) -> None:
        if cls._icons:
            return
        assets = BASE_DIR / "assets"
        show_path = assets / "ojo.png"
        hide_path = assets / "invisible.png"
        cls._icons["show"] = tk.PhotoImage(file=str(show_path)).subsample(_SUBSAMPLE, _SUBSAMPLE)
        cls._icons["hide"] = tk.PhotoImage(file=str(hide_path)).subsample(_SUBSAMPLE, _SUBSAMPLE)
        # Evitar que el GC borre las imágenes.
        master._password_field_icons = cls._icons  # type: ignore[attr-defined]

    def _toggle_visibility(self) -> None:
        self._visible = not self._visible
        self.entry.configure(show="" if self._visible else "•")
        self._toggle.configure(image=self._icons["show"] if self._visible else self._icons["hide"])
