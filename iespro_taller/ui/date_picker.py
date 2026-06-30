"""Selector de fecha simple (sin dependencias extra)."""

import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

from ui.theme import COLORS


class DatePickerRow(ttk.Frame):
    def __init__(
        self,
        master,
        textvariable: tk.StringVar,
        *,
        label: str = "",
        label_width: int = 26,
        on_change=None,
    ):
        super().__init__(master)
        self._on_change = on_change
        if label:
            ttk.Label(self, text=label, width=label_width).pack(side="left")
        self.var = textvariable
        self.entry = ttk.Entry(self, textvariable=textvariable, width=12, state="readonly")
        self.entry.pack(side="left")
        ttk.Button(self, text="Elegir", command=self._open_picker, width=8).pack(side="left", padx=(6, 0))

    def _open_picker(self) -> None:
        DatePickerDialog(self, self.var, on_select=self._on_change)

    def pack_row(self, **kwargs) -> None:
        self.pack(fill="x", pady=2, **kwargs)


class DatePickerDialog(tk.Toplevel):
    def __init__(self, master, target_var: tk.StringVar, *, on_select=None):
        super().__init__(master)
        self.title("Elegir fecha")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()
        self._target = target_var
        self._on_select = on_select

        raw = (target_var.get() or "").strip()
        try:
            self._current = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            self._current = date.today()

        self._year = self._current.year
        self._month = self._current.month

        header = ttk.Frame(self, padding=8)
        header.pack(fill="x")
        ttk.Button(header, text="◀", width=3, command=self._prev_month).pack(side="left")
        self._month_lbl = ttk.Label(header, font=("Helvetica", 11, "bold"))
        self._month_lbl.pack(side="left", expand=True)
        ttk.Button(header, text="▶", width=3, command=self._next_month).pack(side="right")

        self._grid = ttk.Frame(self, padding=(8, 0, 8, 8))
        self._grid.pack()
        self._draw_days()

        ttk.Button(self, text="Hoy", command=self._pick_today).pack(pady=(0, 8))

        self.update_idletasks()
        x = master.winfo_rootx()
        y = master.winfo_rooty() + master.winfo_height()
        self.geometry(f"+{x}+{y}")

    def _month_name(self) -> str:
        months = (
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
        )
        return f"{months[self._month - 1]} {self._year}"

    def _prev_month(self) -> None:
        if self._month == 1:
            self._month = 12
            self._year -= 1
        else:
            self._month -= 1
        self._draw_days()

    def _next_month(self) -> None:
        if self._month == 12:
            self._month = 1
            self._year += 1
        else:
            self._month += 1
        self._draw_days()

    def _draw_days(self) -> None:
        for w in self._grid.winfo_children():
            w.destroy()
        self._month_lbl.configure(text=self._month_name())

        for i, wd in enumerate(["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]):
            ttk.Label(self._grid, text=wd, width=4, anchor="center").grid(row=0, column=i, padx=1, pady=1)

        weeks = calendar.monthcalendar(self._year, self._month)
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    ttk.Label(self._grid, text="", width=4).grid(row=r, column=c)
                    continue
                btn = tk.Button(
                    self._grid,
                    text=str(day),
                    width=3,
                    relief="flat",
                    bg=COLORS["card"],
                    fg=COLORS["text"],
                    activebackground=COLORS["accent"],
                    activeforeground="#ffffff",
                    command=lambda d=day: self._pick(d),
                )
                if (
                    self._year == self._current.year
                    and self._month == self._current.month
                    and day == self._current.day
                ):
                    btn.configure(bg=COLORS["accent"], fg="#ffffff")
                btn.grid(row=r, column=c, padx=1, pady=1)

    def _pick(self, day: int) -> None:
        picked = date(self._year, self._month, day)
        self._target.set(picked.isoformat())
        if self._on_select:
            self._on_select()
        self.destroy()

    def _pick_today(self) -> None:
        today = date.today()
        self._year = today.year
        self._month = today.month
        self._target.set(today.isoformat())
        if self._on_select:
            self._on_select()
        self.destroy()
