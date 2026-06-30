"""Layout lista + panel lateral deslizable (oculto por defecto)."""

import tkinter as tk
from tkinter import ttk

from ui.theme import COLORS


class SidePanelLayout:
    """Lista a la izquierda; formulario en panel derecho al pulsar Crear o Editar."""

    def __init__(self, parent: ttk.Frame, *, panel_width: int = 400):
        self.panel_width = panel_width
        self._visible = False

        self.root = ttk.Frame(parent)
        self.root.pack(fill="both", expand=True)

        self.body = ttk.Frame(self.root)
        self.body.pack(fill="both", expand=True)

        self.list_frame = ttk.Frame(self.body)
        self.list_frame.pack(side="left", fill="both", expand=True)

        self.toolbar = ttk.Frame(self.list_frame)
        self.toolbar.pack(fill="x", pady=(0, 8))

        self.tree_host = ttk.Frame(self.list_frame)
        self.tree_host.pack(fill="both", expand=True)

        self.panel = ttk.LabelFrame(self.body, text="Detalles", padding=12)
        self.panel_form = ttk.Frame(self.panel)
        self.panel_form.pack(fill="both", expand=True)

        footer = ttk.Frame(self.panel)
        footer.pack(fill="x", side="bottom", pady=(12, 0))
        ttk.Button(footer, text="Cerrar", command=self.hide).pack(side="right")

    def frame(self) -> ttk.Frame:
        return self.root

    def show(self, title: str = "Detalles") -> None:
        self.panel.configure(text=title)
        if not self._visible:
            self.panel.pack(side="right", fill="y", padx=(10, 0))
            try:
                self.panel.configure(width=self.panel_width)
            except tk.TclError:
                pass
            self._visible = True

    def hide(self) -> None:
        if self._visible:
            self.panel.pack_forget()
            self._visible = False

    @property
    def visible(self) -> bool:
        return self._visible

    def add_toolbar_button(self, text: str, command, *, accent: bool = True) -> ttk.Button:
        style = "Accent.TButton" if accent else "TButton"
        btn = ttk.Button(self.toolbar, text=text, style=style, command=command)
        btn.pack(side="left", padx=(0, 8))
        return btn
