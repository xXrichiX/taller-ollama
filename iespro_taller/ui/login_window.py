import tkinter as tk
from tkinter import messagebox, ttk


class LoginWindow(tk.Toplevel):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.title("IESPRO-Taller — Login")
        self.geometry("420x260")
        self.resizable(False, False)
        self.on_success = on_success
        self.user = None

        self.transient(master)
        self.grab_set()

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="IESPRO-Taller", font=("Helvetica", 18, "bold")).pack(pady=(0, 10))
        ttk.Label(frame, text="Sistema de citas + asistente IA").pack(pady=(0, 15))

        ttk.Label(frame, text="Email").pack(anchor="w")
        self.email_var = tk.StringVar(value="admin@iespro.mx")
        ttk.Entry(frame, textvariable=self.email_var, width=40).pack(fill="x", pady=(0, 8))

        ttk.Label(frame, text="Contraseña").pack(anchor="w")
        self.pass_var = tk.StringVar(value="admin123")
        ttk.Entry(frame, textvariable=self.pass_var, show="*", width=40).pack(fill="x", pady=(0, 12))

        ttk.Button(frame, text="Entrar", command=self._login).pack(fill="x")
        ttk.Label(frame, text="Demo: admin@iespro.mx / admin123", foreground="gray").pack(pady=8)

    def _login(self):
        from services.catalog_service import login

        user = login(self.email_var.get().strip(), self.pass_var.get().strip())
        if not user:
            messagebox.showerror("Login", "Credenciales inválidas.")
            return
        self.user = user
        self.on_success(user)
        self.destroy()
