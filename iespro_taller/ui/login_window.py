import tkinter as tk
from tkinter import messagebox, ttk

from services.password_policy import MIN_PASSWORD_LEN, normalize_password
from ui.password_field import PasswordField
from ui.theme import COLORS


class LoginFrame(ttk.Frame):
    """Pantalla de acceso dentro de la ventana principal (sin ventana flotante)."""

    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success
        self.pack(fill="both", expand=True)

        self.login_email_var = tk.StringVar(self)
        self.login_pass_var = tk.StringVar(self)
        self.reg_nombre_var = tk.StringVar(self)
        self.reg_email_var = tk.StringVar(self)
        self.reg_pass_var = tk.StringVar(self)
        self.reg_codigo_var = tk.StringVar(self)

        self.register_panel: ttk.Frame | None = None
        self.login_email_entry: tk.Entry | None = None

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        box = ttk.Frame(outer, padding=20)
        box.place(relx=0.5, rely=0.48, anchor="center")

        ttk.Label(box, text="IESPRO-Taller", font=("Helvetica", 20, "bold")).pack(pady=(0, 4))
        ttk.Label(box, text="Sistema de citas", foreground=COLORS["muted"]).pack(pady=(0, 20))

        self.body = ttk.Frame(box)
        self.body.pack(fill="x")

        self.login_panel = ttk.Frame(self.body)
        self.login_panel.pack(fill="x")
        self._build_login_panel(self.login_panel)

        self.footer = ttk.Frame(box)
        self.footer.pack(fill="x", pady=(16, 0))

        self.footer_hint = ttk.Label(self.footer, text="¿No tienes cuenta?")
        self.footer_hint.pack()

        self.footer_link = ttk.Label(
            self.footer,
            text="Regístrate",
            foreground=COLORS["accent"],
            cursor="hand2",
            font=("Helvetica", 10, "bold"),
        )
        self.footer_link.pack(pady=(4, 0))
        self.footer_link.bind("<Button-1>", lambda _e: self._show_register())

        self.after_idle(self._focus_email)

    def _text_entry(self, parent: ttk.Frame, var: tk.StringVar, *, width: int = 42) -> tk.Entry:
        entry = tk.Entry(
            parent,
            textvariable=var,
            width=width,
            bg=COLORS["card"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
            font=("Helvetica", 11),
        )
        return entry

    def _field(self, parent: ttk.Frame, label: str, var: tk.StringVar) -> tk.Entry:
        ttk.Label(parent, text=label).pack(anchor="w", pady=(0, 2))
        entry = self._text_entry(parent, var)
        entry.pack(fill="x", ipady=4, pady=(0, 10))
        return entry

    def _password_field(self, parent: ttk.Frame, label: str, var: tk.StringVar, *, hint: str = "") -> None:
        ttk.Label(parent, text=label).pack(anchor="w", pady=(0, 2))
        PasswordField(parent, var, width=42).pack(fill="x", pady=(0, 10))
        if hint:
            ttk.Label(parent, text=hint, foreground=COLORS["muted"], font=("Helvetica", 9)).pack(
                anchor="w", pady=(0, 0)
            )

    def _build_login_panel(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text="Inicio de sesión", padding=16)
        card.pack(fill="x")

        self.login_email_entry = self._field(card, "Correo", self.login_email_var)
        self.login_email_entry.bind("<Return>", lambda _e: self._login())
        self._password_field(card, "Contraseña", self.login_pass_var)

        ttk.Button(card, text="Entrar", style="Accent.TButton", command=self._login).pack(fill="x", pady=(4, 0))

    def _ensure_register_panel(self) -> ttk.Frame:
        if self.register_panel is None:
            self.register_panel = ttk.Frame(self.body)
            self._build_register_panel(self.register_panel)
        return self.register_panel

    def _build_register_panel(self, parent: ttk.Frame) -> None:
        card = ttk.LabelFrame(parent, text="Registro", padding=16)
        card.pack(fill="x")

        self._field(card, "Nombre", self.reg_nombre_var)
        self._field(card, "Correo", self.reg_email_var)
        self._password_field(
            card,
            "Contraseña",
            self.reg_pass_var,
            hint=f"Mínimo {MIN_PASSWORD_LEN} caracteres, con letra y número.",
        )
        self._field(card, "Código de invitación", self.reg_codigo_var)

        ttk.Button(card, text="Crear cuenta", style="Accent.TButton", command=self._register_user).pack(
            fill="x", pady=(4, 8)
        )
        back = ttk.Label(
            card,
            text="Volver al inicio de sesión",
            foreground=COLORS["accent"],
            cursor="hand2",
        )
        back.pack(anchor="w")
        back.bind("<Button-1>", lambda _e: self._show_login())

    def _focus_email(self) -> None:
        if self.login_email_entry and self.login_email_entry.winfo_exists():
            self.login_email_entry.focus_force()

    def _show_register(self) -> None:
        panel = self._ensure_register_panel()
        self.login_panel.pack_forget()
        panel.pack(fill="x")
        self.footer_hint.configure(text="¿Ya tienes cuenta?")
        self.footer_link.configure(text="Inicia sesión aquí")
        self.footer_link.unbind("<Button-1>")
        self.footer_link.bind("<Button-1>", lambda _e: self._show_login())

    def _show_login(self) -> None:
        if self.register_panel is not None:
            self.register_panel.pack_forget()
        self.login_panel.pack(fill="x")
        self.footer_hint.configure(text="¿No tienes cuenta?")
        self.footer_link.configure(text="Regístrate")
        self.footer_link.unbind("<Button-1>")
        self.footer_link.bind("<Button-1>", lambda _e: self._show_register())
        self.after_idle(self._focus_email)

    def _finish_login(self, user: dict) -> None:
        self.on_success(user)

    def _login(self) -> None:
        from services.catalog_service import login

        email = self.login_email_var.get().strip()
        password = normalize_password(self.login_pass_var.get())
        if not email or not password:
            messagebox.showwarning("Iniciar sesión", "Escribe tu correo y contraseña.")
            return

        user = login(email, password)
        if not user:
            messagebox.showerror("Iniciar sesión", "Correo o contraseña incorrectos.")
            return
        if user.get("rol_nombre") == "PENDIENTE":
            messagebox.showinfo(
                "Cuenta pendiente",
                "Tu cuenta aún no tiene puesto asignado. Contacta al administrador de tu taller.",
            )
            return
        self._finish_login(user)

    def _register_user(self) -> None:
        from services.catalog_service import login, register_usuario

        nombre = self.reg_nombre_var.get().strip()
        email = self.reg_email_var.get().strip().lower()
        password = normalize_password(self.reg_pass_var.get())

        codigo = self.reg_codigo_var.get().strip()

        result = register_usuario(nombre, email, password, codigo)
        if not result.get("ok"):
            messagebox.showerror("Registro", result.get("error", "No se pudo crear la cuenta."))
            return

        if result.get("pendiente_rol"):
            sucursal = result.get("sucursal") or "tu taller"
            messagebox.showinfo(
                "Registro",
                f"Cuenta creada en {sucursal}.\n\n"
                "Un administrador debe asignarte tu puesto antes de que puedas entrar.",
            )
            self._show_login()
            return

        user = login(email, password)
        if user:
            messagebox.showinfo("Registro", "Cuenta creada. Bienvenido.")
            self._finish_login(user)
            return

        messagebox.showinfo(
            "Registro",
            "Cuenta creada. Ya puedes iniciar sesión con tu correo y contraseña.",
        )
        self._show_login()


# Alias por compatibilidad
LoginWindow = LoginFrame
