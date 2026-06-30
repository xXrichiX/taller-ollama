"""Campo de contraseña con icono para mostrar/ocultar."""

import tkinter as tk

from config import BASE_DIR
from ui.theme import COLORS

_ICON_SIZE = 16
_SUBSAMPLE = 32  # 512px → 16px


def _entry_style() -> dict:
    return {
        "bg": COLORS["card"],
        "fg": COLORS["text"],
        "insertbackground": COLORS["text"],
        "relief": "solid",
        "borderwidth": 1,
        "highlightthickness": 1,
        "highlightbackground": COLORS["border"],
        "highlightcolor": COLORS["accent"],
        "font": ("Helvetica", 11),
    }


class PasswordField(tk.Frame):
    _icons: dict[str, tk.PhotoImage] = {}

    def __init__(self, master, textvariable: tk.StringVar, *, width: int = 42):
        super().__init__(master, bg=COLORS["bg"])
        self._visible = False
        self._ensure_icons(master)

        self.entry = tk.Entry(
            self,
            textvariable=textvariable,
            show="•",
            width=width,
            **_entry_style(),
        )
        self.entry.pack(fill="x", ipady=4)

        self._toggle = tk.Label(
            self.entry,
            image=self._icons["hide"],
            cursor="hand2",
            bg=COLORS["card"],
        )
        self._toggle.place(relx=1.0, rely=0.5, anchor="e", x=-8)
        self._toggle.bind("<Button-1>", lambda _e: self._toggle_visibility())
        self._toggle.lift()

    @classmethod
    def _ensure_icons(cls, master: tk.Misc) -> None:
        if cls._icons:
            return
        assets = BASE_DIR / "assets"
        show_path = assets / "ojo.png"
        hide_path = assets / "invisible.png"
        cls._icons["show"] = tk.PhotoImage(file=str(show_path)).subsample(_SUBSAMPLE, _SUBSAMPLE)
        cls._icons["hide"] = tk.PhotoImage(file=str(hide_path)).subsample(_SUBSAMPLE, _SUBSAMPLE)
        master._password_field_icons = cls._icons  # type: ignore[attr-defined]

    def _toggle_visibility(self) -> None:
        self._visible = not self._visible
        self.entry.configure(show="" if self._visible else "•")
        self._toggle.configure(image=self._icons["show"] if self._visible else self._icons["hide"])
