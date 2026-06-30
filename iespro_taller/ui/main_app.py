import tkinter as tk
from tkinter import messagebox, ttk

from config import DEFAULT_SUCURSAL_ID
from services import catalog_service, cita_service
from services.chat_service import ChatService
from services.estado_labels import ESTADOS_MECANICO_UI, ESTADOS_UI, estado_a_etiqueta, etiqueta_a_estado
from services.user_roles import (
    can_manage_branch,
    is_cliente,
    is_mecanico,
    is_pending,
    is_staff_manager,
    is_super_admin,
    is_workshop_staff,
)
from ui.chat_window import ChatWindow
from ui.login_window import LoginFrame
from ui.theme import COLORS, apply_theme, set_button_enabled, style_listbox
from ui.user_menu import UserProfileMenu


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_theme(self)
        self.title("IESPRO-Taller")
        self.geometry("540x580")
        self.minsize(500, 520)

        self.user = None
        self.id_sucursal = DEFAULT_SUCURSAL_ID
        self.chat_service = ChatService(self.id_sucursal)
        self.chat_window = None
        self.user_menu: UserProfileMenu | None = None

        # Barra de estado de BD/RAG desactivada en UI para demo limpia.
        # La inicialización sigue ejecutándose en _init_db().
        # self.status_var = tk.StringVar(value="Iniciando...")
        # ttk.Label(self, textvariable=self.status_var, style="Status.TLabel", anchor="w").pack(
        #     side="bottom", fill="x", ipady=4
        # )

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self._init_db()
        LoginFrame(self.container, self._on_login)
    def _init_db(self):
        from db.init_db import ensure_data_dir, init_database

        ensure_data_dir()
        ok, _ = init_database()
        # self.status_var.set(msg if ok else f"BD: {msg}")

        if ok:
            self.chat_service.bootstrap()

    def _on_login(self, user):
        if is_pending(user.get("rol_nombre")):
            messagebox.showinfo(
                "Cuenta pendiente",
                "Tu cuenta fue creada correctamente.\n\n"
                "Un administrador debe asignarte tu rol (cliente, mecánico o administrador) "
                "antes de que puedas usar el sistema. Intenta iniciar sesión más tarde.",
            )
            return

        self.user = user
        self.id_cliente = None
        if is_cliente(user.get("rol_nombre")) and user.get("id"):
            cliente = catalog_service.get_cliente_by_usuario(user["id"])
            self.id_cliente = cliente["id"] if cliente else None
        if user.get("id_sucursal"):
            self.id_sucursal = user["id_sucursal"]
            self.chat_service.id_sucursal = self.id_sucursal
        self.chat_service.set_user(user)

        for w in self.container.winfo_children():
            w.destroy()

        self._maximize_window()
        self._build_main_shell(user)

    def _maximize_window(self) -> None:
        self.update_idletasks()
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        self.geometry(f"{w}x{h}")
        self.minsize(900, 600)

    def _build_main_shell(self, user: dict) -> None:
        sucursal_nombre = self._sucursal_nombre()
        self._build_header(user, sucursal_nombre)

        notebook = ttk.Notebook(self.container)
        notebook.pack(fill="both", expand=True, padx=0, pady=0)

        notebook.add(self._build_dashboard_tab(), text="  Inicio  ")

        if is_super_admin(user.get("rol_nombre")):
            notebook.add(self._build_sucursales_tab(), text="  Sucursales  ")

        if can_manage_branch(user.get("rol_nombre")):
            notebook.add(self._build_clientes_tab(), text="  Clientes  ")

        if is_cliente(user.get("rol_nombre")):
            veh_label = "  Mis Vehículos  "
            cita_label = "  Mis Citas  "
        elif is_mecanico(user.get("rol_nombre")):
            veh_label = "  Vehículos (sucursal)  "
            cita_label = "  Órdenes de trabajo  "
        else:
            veh_label = "  Vehículos  "
            cita_label = "  Citas  "

        if not is_cliente(user.get("rol_nombre")):
            notebook.add(self._build_vehiculos_tab(), text=veh_label)
        elif is_cliente(user.get("rol_nombre")):
            notebook.add(self._build_vehiculos_tab(), text=veh_label)

        notebook.add(self._build_citas_tab(), text=cita_label)

        if can_manage_branch(user.get("rol_nombre")):
            notebook.add(self._build_taller_tab(), text="  Mi Taller  ")
        if is_staff_manager(user.get("rol_nombre")):
            notebook.add(self._build_usuarios_tab(), text="  Usuarios  ")

    def _build_header(self, user: dict, sucursal_nombre: str) -> None:
        header = tk.Frame(self.container, bg=COLORS["header"], padx=20, pady=14)
        header.pack(fill="x")

        left = tk.Frame(header, bg=COLORS["header"])
        left.pack(side="left", fill="x", expand=True)

        self.user_menu = UserProfileMenu(
            left,
            nombre=user["nombre"],
            rol=user["rol_nombre"],
            on_profile=self._show_profile,
            on_logout=self._logout,
        )
        self.user_menu.pack(anchor="w")

        ttk.Button(
            header,
            text="Abrir asistente IA",
            style="Accent.TButton",
            command=self._open_chat,
        ).pack(side="right")

    def _show_profile(self) -> None:
        if not self.user:
            return
        u = self.user
        puesto = u.get("puesto_nombre") or "— Sin puesto —"
        messagebox.showinfo(
            "Mi Perfil",
            f"Nombre: {u['nombre']}\n"
            f"Correo: {u['email']}\n"
            f"Rol (permisos): {u['rol_nombre']}\n"
            f"Puesto en el taller: {puesto}\n"
            f"Sucursal: {self._sucursal_nombre()}",
        )

    def _logout(self) -> None:
        if self.user_menu:
            self.user_menu.close_menu()

        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.destroy()
        self.chat_window = None
        self.user = None
        self.user_menu = None
        self.id_sucursal = DEFAULT_SUCURSAL_ID
        self.chat_service = ChatService(self.id_sucursal)

        for w in self.container.winfo_children():
            w.destroy()

        self.geometry("540x580")
        self.minsize(500, 520)
        LoginFrame(self.container, self._on_login)

    def _sucursal_nombre(self):
        for s in catalog_service.list_sucursales():
            if s["id"] == self.id_sucursal:
                return s["nombre"]
        return f"Sucursal {self.id_sucursal}"

    def _open_chat(self):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            self.chat_window.focus_force()
            return
        self.chat_service.ensure_conversation()
        self.chat_window = ChatWindow(self, self.chat_service)
    def _build_dashboard_tab(self):
        frame = ttk.Frame(padding=12)

        header_row = ttk.Frame(frame)
        header_row.pack(fill="x", pady=(0, 12))
        ttk.Label(header_row, text=self._dashboard_title(), font=("Helvetica", 16, "bold")).pack(side="left")
        ttk.Button(header_row, text="Actualizar", command=self._refresh_dashboard).pack(side="right")

        self.dash_cards = ttk.Frame(frame)
        self.dash_cards.pack(fill="x", pady=(0, 12))

        ttk.Label(frame, text="Citas recientes", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        self.dash_citas_tree = self._make_tree(
            frame,
            ("cliente", "placa", "estado", "mecanico", "isla", "descripcion_fallo"),
            headers={
                "cliente": "Cliente",
                "placa": "Placa",
                "estado": "Estado",
                "mecanico": "Mecánico",
                "isla": "Isla",
                "descripcion_fallo": "Falla",
            },
            height=20,
        )

        self._refresh_dashboard()
        return frame

    def _dashboard_title(self) -> str:
        if self.user and is_cliente(self.user.get("rol_nombre")):
            return "Mi panel"
        if self.user and is_mecanico(self.user.get("rol_nombre")):
            return "Panel del mecánico"
        return "Panel del taller"

    def _is_super_admin_user(self) -> bool:
        return bool(self.user and is_super_admin(self.user.get("rol_nombre")))

    def _is_cliente_user(self) -> bool:
        return bool(self.user and is_cliente(self.user.get("rol_nombre")))

    def _is_mecanico_user(self) -> bool:
        return bool(self.user and is_mecanico(self.user.get("rol_nombre")))

    def _citas_filters(self) -> dict:
        filters: dict = {}
        if self._is_cliente_user() and self.id_cliente:
            filters["id_cliente"] = self.id_cliente
        if not self._is_super_admin_user():
            filters["id_sucursal"] = self.id_sucursal
        return filters

    def _can_reassign_citas(self) -> bool:
        return bool(self.user and can_manage_branch(self.user.get("rol_nombre")))

    def _can_manage_citas(self) -> bool:
        return bool(self.user and is_workshop_staff(self.user.get("rol_nombre")))

    def _can_create_citas(self) -> bool:
        return bool(self.user and can_manage_branch(self.user.get("rol_nombre")))

    def _stat_card(self, parent, title: str, value_var: tk.StringVar, accent: bool = False):
        outer = tk.Frame(parent, bg=COLORS["border"], padx=1, pady=1)
        outer.pack(side="left", fill="both", expand=True, padx=(0, 10))
        card = tk.Frame(outer, bg=COLORS["card"], padx=14, pady=12)
        card.pack(fill="both", expand=True)
        tk.Label(card, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=("Helvetica", 10)).pack(anchor="w")
        fg = COLORS["accent"] if accent else COLORS["header"]
        tk.Label(card, textvariable=value_var, bg=COLORS["card"], fg=fg, font=("Helvetica", 22, "bold")).pack(anchor="w", pady=(4, 0))
        return outer

    def _refresh_dashboard(self):
        filters = self._citas_filters()
        citas = cita_service.list_citas(**filters)
        id_cliente = filters.get("id_cliente")
        vehiculos: list = []
        if id_cliente:
            vehiculos = cita_service.list_vehiculos(id_cliente=id_cliente)
        elif self._is_mecanico_user() or (can_manage_branch(self.user.get("rol_nombre")) and not self._is_super_admin_user()):
            vehiculos = cita_service.list_vehiculos(id_sucursal=self.id_sucursal)
        elif self._is_super_admin_user():
            vehiculos = cita_service.list_vehiculos()

        if self._is_cliente_user() or self._is_mecanico_user():
            clientes = []
            islas = []
            mecanicos = []
        elif self._is_super_admin_user():
            clientes = catalog_service.list_clientes()
            islas = []
            mecanicos = []
        else:
            clientes = catalog_service.list_clientes()
            islas = cita_service.list_islas(self.id_sucursal)
            mecanicos = cita_service.list_mecanicos(self.id_sucursal)

        pendientes = sum(1 for c in citas if c["estado"] in ("PENDIENTE", "RECIBIDO"))
        en_proceso = sum(1 for c in citas if c["estado"] in ("EN_PROCESO", "DIAGNOSTICO", "EN_REPARACION", "ESPERANDO_REFACCIONES"))
        completadas = sum(1 for c in citas if c["estado"] in ("COMPLETADA", "FINALIZADO"))

        if not hasattr(self, "dash_stat_vars"):
            self.dash_stat_vars = {}
            for w in self.dash_cards.winfo_children():
                w.destroy()
            row1 = ttk.Frame(self.dash_cards)
            row1.pack(fill="x")
            if self._is_cliente_user():
                self.dash_stat_vars["vehiculos"] = tk.StringVar(value="0")
                self.dash_stat_vars["citas"] = tk.StringVar(value="0")
                self.dash_stat_vars["pendientes"] = tk.StringVar(value="0")
                self._stat_card(row1, "Mis vehículos", self.dash_stat_vars["vehiculos"])
                self._stat_card(row1, "Mis citas", self.dash_stat_vars["citas"], accent=True)
                self._stat_card(row1, "Pendientes", self.dash_stat_vars["pendientes"], accent=True)
                row2 = ttk.Frame(self.dash_cards)
                row2.pack(fill="x", pady=(10, 0))
                self.dash_stat_vars["proceso"] = tk.StringVar(value="0")
                self.dash_stat_vars["completadas"] = tk.StringVar(value="0")
                self._stat_card(row2, "En proceso", self.dash_stat_vars["proceso"])
                self._stat_card(row2, "Completadas", self.dash_stat_vars["completadas"])
            elif self._is_mecanico_user():
                self.dash_stat_vars["citas"] = tk.StringVar(value="0")
                self.dash_stat_vars["pendientes"] = tk.StringVar(value="0")
                self.dash_stat_vars["proceso"] = tk.StringVar(value="0")
                self._stat_card(row1, "Órdenes en sucursal", self.dash_stat_vars["citas"], accent=True)
                self._stat_card(row1, "Pendientes", self.dash_stat_vars["pendientes"], accent=True)
                self._stat_card(row1, "En proceso", self.dash_stat_vars["proceso"])
                row2 = ttk.Frame(self.dash_cards)
                row2.pack(fill="x", pady=(10, 0))
                self.dash_stat_vars["completadas"] = tk.StringVar(value="0")
                self._stat_card(row2, "Completadas", self.dash_stat_vars["completadas"])
            else:
                self.dash_stat_vars = {
                    "clientes": tk.StringVar(value="0"),
                    "vehiculos": tk.StringVar(value="0"),
                    "citas": tk.StringVar(value="0"),
                    "pendientes": tk.StringVar(value="0"),
                    "proceso": tk.StringVar(value="0"),
                    "mecanicos": tk.StringVar(value="0"),
                }
                self._stat_card(row1, "Clientes", self.dash_stat_vars["clientes"])
                self._stat_card(row1, "Vehículos", self.dash_stat_vars["vehiculos"])
                self._stat_card(row1, "Citas totales", self.dash_stat_vars["citas"], accent=True)
                self._stat_card(row1, "Pendientes", self.dash_stat_vars["pendientes"], accent=True)
                row2 = ttk.Frame(self.dash_cards)
                row2.pack(fill="x", pady=(10, 0))
                self._stat_card(row2, "En proceso", self.dash_stat_vars["proceso"])
                self.dash_stat_vars["completadas"] = tk.StringVar(value="0")
                self.dash_stat_vars["islas"] = tk.StringVar(value="0")
                self._stat_card(row2, "Completadas", self.dash_stat_vars["completadas"])
                self._stat_card(row2, "Islas activas", self.dash_stat_vars["islas"])
                self._stat_card(row2, "Mecánicos", self.dash_stat_vars["mecanicos"])

        if self._is_cliente_user():
            self.dash_stat_vars["vehiculos"].set(str(len(vehiculos)))
            self.dash_stat_vars["citas"].set(str(len(citas)))
            self.dash_stat_vars["pendientes"].set(str(pendientes))
            self.dash_stat_vars["proceso"].set(str(en_proceso))
            self.dash_stat_vars["completadas"].set(str(completadas))
        elif self._is_mecanico_user():
            self.dash_stat_vars["citas"].set(str(len(citas)))
            self.dash_stat_vars["pendientes"].set(str(pendientes))
            self.dash_stat_vars["proceso"].set(str(en_proceso))
            self.dash_stat_vars["completadas"].set(str(completadas))
        else:
            self.dash_stat_vars["clientes"].set(str(len(clientes)))
            self.dash_stat_vars["vehiculos"].set(str(len(vehiculos)))
            self.dash_stat_vars["citas"].set(str(len(citas)))
            self.dash_stat_vars["pendientes"].set(str(pendientes))
            self.dash_stat_vars["proceso"].set(str(en_proceso))
            self.dash_stat_vars["completadas"].set(str(completadas))
            self.dash_stat_vars["islas"].set(str(len(islas)))
            self.dash_stat_vars["mecanicos"].set(str(len(mecanicos)))

        rows = []
        for c in citas[:12]:
            rows.append({
                "id": c["id"],
                "cliente": c["cliente"],
                "placa": c["placa"],
                "estado": estado_a_etiqueta(c["estado"]),
                "mecanico": c["mecanico"],
                "isla": c["isla"],
                "descripcion_fallo": (c["descripcion_fallo"] or "")[:70],
            })
        self._fill_tree(self.dash_citas_tree, rows)

    def _build_clientes_tab(self):
        frame = ttk.Frame(padding=10)
        top = ttk.LabelFrame(frame, text="Nuevo cliente", padding=10)
        top.pack(fill="x")

        self.cli_nombre = tk.StringVar()
        self.cli_tel = tk.StringVar()
        self.cli_email = tk.StringVar()
        self.cli_usuario_map = {}

        for label, var in [("Nombre", self.cli_nombre), ("Teléfono", self.cli_tel), ("Email", self.cli_email)]:
            row = ttk.Frame(top)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

        ttk.Label(
            top,
            text="Si el cliente no usa la app, deja «Sin usuario» y registra su vehículo después.",
            wraplength=520,
        ).pack(anchor="w", pady=(0, 6))
        self.cli_usuario_cb = self._add_combo_row(top, "Usuario vinculado (opcional)", width=14)
        self._reload_cliente_usuarios()
        ttk.Button(top, text="Guardar cliente", command=self._save_cliente).pack(anchor="e", pady=8)

        self.clientes_tree = self._make_tree(
            frame,
            ("nombre", "telefono", "email", "usuario_email"),
            headers={"nombre": "Nombre", "telefono": "Teléfono", "email": "Email", "usuario_email": "Usuario"},
        )
        self._load_clientes()
        return frame

    def _reload_cliente_usuarios(self):
        usuarios = [u for u in catalog_service.list_usuarios() if u.get("es_cliente")]
        opciones = [{"id": None, "nombre": "— Sin usuario (mostrador) —", "email": ""}] + [
            {"id": u["id"], "nombre": u["nombre"], "email": u["email"]} for u in usuarios
        ]
        self.cli_usuario_map = self._fill_combo(
            self.cli_usuario_cb,
            opciones,
            lambda u: u["nombre"] if u["id"] else "— Sin usuario (mostrador) —",
            "id",
        )

    def _save_cliente(self):
        try:
            sel = self.cli_usuario_cb.get()
            id_usuario = self.cli_usuario_map.get(sel)
            if id_usuario == "":
                id_usuario = None
            catalog_service.create_cliente(
                self.cli_nombre.get().strip(),
                self.cli_tel.get().strip(),
                self.cli_email.get().strip(),
                id_usuario,
            )
            messagebox.showinfo("Clientes", "Cliente guardado.")
            self._load_clientes()
            self._reload_cliente_usuarios()
            if hasattr(self, "c_cliente_cb"):
                self._reload_cita_clientes()
        except Exception as exc:
            messagebox.showerror("Clientes", str(exc))

    def _load_clientes(self):
        self._fill_tree(self.clientes_tree, catalog_service.list_clientes())

    def _build_vehiculos_tab(self):
        frame = ttk.Frame(padding=10)
        can_edit = self._can_create_citas() or self._is_cliente_user()

        if self._is_cliente_user():
            ttk.Label(
                frame,
                text="Tus vehículos registrados. El estado de cada cita y el mecánico asignado están en Mis Citas.",
                foreground=COLORS["muted"],
                wraplength=700,
            ).pack(anchor="w", pady=(0, 8))
        elif self._is_mecanico_user():
            ttk.Label(
                frame,
                text="Consulta todos los vehículos de tu sucursal. Solo puedes trabajar los asignados a ti.",
                foreground=COLORS["muted"],
                wraplength=700,
            ).pack(anchor="w", pady=(0, 8))

        self.v_num = tk.StringVar()
        self.v_placa = tk.StringVar()
        self.v_serie = tk.StringVar()
        self.v_modelo = tk.StringVar()
        self.v_km = tk.StringVar(value="0")
        self.v_dias = tk.StringVar(value="90")
        self.v_obs = tk.StringVar()
        self.v_cliente_map = {}
        self.v_marca_map = {}
        self.v_comb_map = {}
        self.v_unidad_map = {}
        self.v_mecanico_map = {}
        self.v_cliente_cb = None
        self.v_mecanico_cb = None
        self.v_marca_cb = None
        self.v_comb_cb = None
        self.v_unidad_cb = None

        if can_edit:
            form_title = "Registrar mi vehículo" if self._is_cliente_user() else "Registrar vehículo"
            form = ttk.LabelFrame(frame, text=form_title, padding=10)
            form.pack(fill="x")

            if self._is_cliente_user() and not self.id_cliente:
                ttk.Label(
                    form,
                    text="No encontramos tu ficha de cliente. Cierra sesión e intenta de nuevo.",
                    foreground=COLORS["muted"],
                ).pack(anchor="w")

            text_fields = [
                ("No. económico", self.v_num), ("Placa", self.v_placa), ("Serie", self.v_serie),
                ("Modelo", self.v_modelo), ("Kilometraje", self.v_km), ("Días mant.", self.v_dias),
                ("Observaciones", self.v_obs),
            ]
            for label, var in text_fields:
                row = ttk.Frame(form)
                row.pack(fill="x", pady=2)
                ttk.Label(row, text=label, width=18).pack(side="left")
                ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

            if not self._is_cliente_user():
                self.v_cliente_cb = self._add_combo_row(form, "Propietario (cliente)", width=18)
                self.v_mecanico_cb = self._add_combo_row(form, "Mecánico asignado", width=18)
            self.v_marca_cb = self._add_combo_row(form, "Marca", width=18)
            self.v_comb_cb = self._add_combo_row(form, "Tipo combustible", width=18)
            self.v_unidad_cb = self._add_combo_row(form, "Tipo unidad", width=18)

            self._reload_vehiculo_combos()
            ttk.Button(form, text="Guardar vehículo", command=self._save_vehiculo).pack(anchor="e", pady=6)

        cols = ("placa", "marca", "modelo", "cliente", "mecanico_asignado", "numero_economico", "kilometraje")
        headers = {
            "placa": "Placa", "marca": "Marca", "modelo": "Modelo", "cliente": "Cliente",
            "mecanico_asignado": "Mecánico", "numero_economico": "No. económico", "kilometraje": "Km",
        }
        if self._is_cliente_user():
            cols = ("placa", "marca", "modelo", "cliente", "numero_economico", "kilometraje")
            headers = {
                "placa": "Placa", "marca": "Marca", "modelo": "Modelo",
                "cliente": "Cliente", "numero_economico": "No. económico", "kilometraje": "Km",
            }

        self.veh_tree = self._make_tree(frame, cols, headers=headers)
        self._load_vehiculos()
        return frame

    def _reload_vehiculo_combos(self):
        if not self._is_cliente_user() and self.v_cliente_cb is not None:
            clientes = catalog_service.list_clientes()
            self.v_cliente_map = self._fill_combo(
                self.v_cliente_cb,
                clientes,
                lambda c: f"{c['nombre']} — {c.get('telefono') or c.get('email') or 'sin contacto'}",
                "id",
            )
        if self.v_mecanico_cb is not None:
            mecanicos = cita_service.list_mecanicos(self.id_sucursal)
            opciones = [{"id": None, "nombre": "— Sin asignar —"}] + mecanicos
            self.v_mecanico_map = self._fill_combo(
                self.v_mecanico_cb,
                opciones,
                lambda m: m["nombre"] if m.get("id") else "— Sin asignar —",
                "id",
            )
        marcas = catalog_service.list_marcas()
        self.v_marca_map = self._fill_combo(self.v_marca_cb, marcas, lambda m: m["nombre"], "id")
        combs = catalog_service.list_tipos_combustible()
        self.v_comb_map = self._fill_combo(self.v_comb_cb, combs, lambda t: t["nombre"], "id")
        unidades = catalog_service.list_tipos_unidad()
        self.v_unidad_map = self._fill_combo(self.v_unidad_cb, unidades, lambda t: t["nombre"], "id")

    def _save_vehiculo(self):
        try:
            if self._is_cliente_user():
                if not self.id_cliente:
                    raise ValueError("No se encontró tu ficha de cliente.")
                id_cliente = self.id_cliente
            else:
                id_cliente = self._combo_id(self.v_cliente_cb, self.v_cliente_map, "cliente")
            id_usuario = catalog_service.ensure_cliente_usuario(id_cliente)

            id_mecanico = None
            if self.v_mecanico_cb and self.v_mecanico_map:
                sel = self.v_mecanico_cb.get()
                id_mecanico = self.v_mecanico_map.get(sel)

            cita_service.create_vehiculo({
                "numero_economico": self.v_num.get().strip(),
                "placa": self.v_placa.get().strip(),
                "serie": self.v_serie.get().strip(),
                "modelo": self.v_modelo.get().strip(),
                "kilometraje": int(self.v_km.get()),
                "dias_mantenimiento": int(self.v_dias.get()),
                "observaciones": self.v_obs.get().strip() or None,
                "id_cliente": id_cliente,
                "id_usuario": id_usuario,
                "id_sucursal": self.id_sucursal,
                "id_mecanico_asignado": id_mecanico,
                "id_marca": self._combo_id(self.v_marca_cb, self.v_marca_map, "marca"),
                "id_tipo_combustible": self._combo_id(self.v_comb_cb, self.v_comb_map, "combustible"),
                "id_tipo_unidad": self._combo_id(self.v_unidad_cb, self.v_unidad_map, "tipo unidad"),
            })
            self.chat_service.rag.sync_fallas_from_db()
            messagebox.showinfo("Vehículos", "Vehículo registrado.")
            self._load_vehiculos()
            if hasattr(self, "c_cliente_cb"):
                self._reload_cita_clientes()
        except Exception as exc:
            messagebox.showerror("Vehículos", str(exc))

    def _load_vehiculos(self):
        if self._is_cliente_user():
            rows = cita_service.list_vehiculos(id_cliente=self.id_cliente)
        elif self._is_super_admin_user():
            rows = cita_service.list_vehiculos()
        else:
            rows = cita_service.list_vehiculos(id_sucursal=self.id_sucursal)
        self._fill_tree(self.veh_tree, rows)

    def _build_citas_tab(self):
        frame = ttk.Frame(padding=10)
        self.c_fecha = tk.StringVar(value="2026-06-11")
        self.c_fallo = tk.StringVar()
        self.c_fcomp = tk.StringVar(value="2026-06-11")
        self.c_hcomp = tk.StringVar(value="18:00:00")
        self.c_cliente_map = {}
        self.c_vehiculo_map = {}
        self.c_horario_map = {}
        self.c_mecanico_map = {}
        self.c_isla_map = {}
        self.c_servicio_rows = []
        self.c_cliente_cb = None
        self.c_mecanico_cb = None
        self.c_isla_cb = None
        self.c_vehiculo_cb = None
        self.c_horario_cb = None
        self.c_servicios_lb = None

        if self._can_create_citas() or self._is_cliente_user():
            form_title = "Solicitar cita" if self._is_cliente_user() else "Nueva cita"
            form = ttk.LabelFrame(frame, text=form_title, padding=10)
            form.pack(fill="x")

            if self._can_create_citas():
                self.c_cliente_cb = self._add_combo_row(form, "Cliente")
                self.c_cliente_cb.bind("<<ComboboxSelected>>", lambda e: self._reload_cita_vehiculos())
            elif self._is_cliente_user():
                ttk.Label(
                    form,
                    text="El taller asignará mecánico e isla después de tu solicitud.",
                    foreground=COLORS["muted"],
                ).pack(anchor="w", pady=(0, 6))

            self.c_vehiculo_cb = self._add_combo_row(form, "Vehículo")

            row = ttk.Frame(form)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text="Fecha cita", width=26).pack(side="left")
            ttk.Entry(row, textvariable=self.c_fecha, width=14).pack(side="left")
            ttk.Button(row, text="Cargar horarios", command=self._reload_cita_horarios).pack(side="left", padx=8)

            self.c_horario_cb = self._add_combo_row(form, "Hora de la cita")
            if self._can_create_citas():
                self.c_mecanico_cb = self._add_combo_row(form, "Mecánico asignado")
                self.c_isla_cb = self._add_combo_row(form, "Isla asignada")

            row = ttk.Frame(form)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text="Descripción del fallo", width=26).pack(side="left", anchor="n")
            ttk.Entry(row, textvariable=self.c_fallo).pack(side="left", fill="x", expand=True)

            row = ttk.Frame(form)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text="Fecha compromiso", width=26).pack(side="left")
            ttk.Entry(row, textvariable=self.c_fcomp, width=14).pack(side="left")
            ttk.Label(row, text="Hora compromiso").pack(side="left", padx=(12, 4))
            ttk.Entry(row, textvariable=self.c_hcomp, width=10).pack(side="left")

            row = ttk.Frame(form)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text="Tipos de mantenimiento", width=26).pack(side="left", anchor="n")
            serv_wrap = ttk.Frame(row)
            serv_wrap.pack(side="left", fill="x", expand=True)
            self.c_servicios_lb = tk.Listbox(serv_wrap, selectmode=tk.EXTENDED, height=5, exportselection=False)
            style_listbox(self.c_servicios_lb)
            self.c_servicios_lb.pack(side="left", fill="x", expand=True)
            scroll = ttk.Scrollbar(serv_wrap, orient="vertical", command=self.c_servicios_lb.yview)
            scroll.pack(side="right", fill="y")
            self.c_servicios_lb.configure(yscrollcommand=scroll.set)

            btn_text = "Solicitar cita" if self._is_cliente_user() else "Crear cita"
            ttk.Button(form, text=btn_text, command=self._save_cita).pack(anchor="e", pady=6)
        elif self._is_mecanico_user():
            ttk.Label(
                frame,
                text="Ves todas las órdenes de tu sucursal. Solo puedes modificar las asignadas a ti.",
                foreground=COLORS["muted"],
                wraplength=700,
            ).pack(anchor="w", pady=(0, 8))

        if self._is_cliente_user():
            ttk.Label(
                frame,
                text="Aquí verás el estado de tus citas y el mecánico asignado cuando el taller lo confirme.",
                foreground=COLORS["muted"],
                wraplength=700,
            ).pack(anchor="w", pady=(0, 8))

        self._reload_cita_form()

        if self._is_cliente_user():
            citas_cols = ("placa", "fecha_cita", "estado", "mecanico", "isla", "descripcion_fallo")
            citas_headers = {
                "placa": "Placa", "fecha_cita": "Fecha", "estado": "Estado",
                "mecanico": "Mecánico asignado", "isla": "Isla",
                "descripcion_fallo": "Falla reportada",
            }
        else:
            citas_cols = ("cliente", "placa", "fecha_cita", "estado", "mecanico", "isla", "descripcion_fallo")
            citas_headers = {
                "cliente": "Cliente", "placa": "Placa", "fecha_cita": "Fecha",
                "estado": "Estado", "mecanico": "Mecánico", "isla": "Isla",
                "descripcion_fallo": "Falla reportada",
            }

        self.citas_tree = self._make_tree(frame, citas_cols, headers=citas_headers)
        self.citas_tree.bind("<<TreeviewSelect>>", self._on_cita_selected)

        if self._can_manage_citas():
            manage_title = (
                "Actualizar estado de la cita"
                if self._is_mecanico_user()
                else "Actualizar cita seleccionada"
            )
            manage = ttk.LabelFrame(frame, text=manage_title, padding=10)
            manage.pack(fill="x", pady=(0, 8))
            self.c_manage_estado = tk.StringVar()
            self.c_manage_diagnostico = tk.StringVar()
            self.c_manage_observaciones = tk.StringVar()
            self.c_manage_solucion = tk.StringVar()
            self.c_manage_mec_map = {}
            self.c_manage_isla_map = {}
            self.c_manage_mec_cb = None
            self.c_manage_isla_cb = None
            estados_vals = ESTADOS_MECANICO_UI if self._is_mecanico_user() else ESTADOS_UI
            row = ttk.Frame(manage)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text="Estado", width=14).pack(side="left")
            self.c_manage_estado_cb = ttk.Combobox(
                row, textvariable=self.c_manage_estado, values=estados_vals, state="readonly", width=18,
            )
            self.c_manage_estado_cb.pack(side="left")
            if self._is_mecanico_user():
                for label, var in [
                    ("Diagnóstico", self.c_manage_diagnostico),
                    ("Observaciones", self.c_manage_observaciones),
                    ("Solución", self.c_manage_solucion),
                ]:
                    row = ttk.Frame(manage)
                    row.pack(fill="x", pady=2)
                    ttk.Label(row, text=label, width=14).pack(side="left", anchor="n")
                    ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)
            if self._can_reassign_citas():
                self.c_manage_mec_cb = self._add_combo_row(manage, "Mecánico", width=14)
                self.c_manage_isla_cb = self._add_combo_row(manage, "Isla", width=14)
                self._reload_cita_manage_combos()
            hint = (
                "Selecciona una orden asignada a ti para actualizar estado, diagnóstico u observaciones."
                if self._is_mecanico_user()
                else "Selecciona una cita de la lista para cambiar estado, mecánico o isla."
            )
            ttk.Button(manage, text="Guardar cambios", command=self._update_cita_staff).pack(anchor="e", pady=6)
            ttk.Label(manage, text=hint, foreground=COLORS["muted"]).pack(anchor="w")

        self._load_citas()
        return frame

    def _reload_cita_manage_combos(self):
        if not self._can_reassign_citas() or not hasattr(self, "c_manage_mec_cb") or not self.c_manage_mec_cb:
            return
        mecanicos = cita_service.list_mecanicos(self.id_sucursal)
        self.c_manage_mec_map = self._fill_combo(self.c_manage_mec_cb, mecanicos, lambda m: m["nombre"], "id")
        islas = cita_service.list_islas(self.id_sucursal)
        self.c_manage_isla_map = self._fill_combo(self.c_manage_isla_cb, islas, lambda i: i["nombre"], "id")

    def _on_cita_selected(self, _event=None) -> None:
        if not self._can_manage_citas() or not hasattr(self, "c_manage_estado_cb"):
            return
        sel = self.citas_tree.selection()
        if not sel:
            return
        id_cita = int(sel[0])
        cita = cita_service.get_cita_by_id(id_cita)
        if not cita:
            return
        self.c_manage_estado.set(estado_a_etiqueta(cita.get("estado")))
        falla = cita_service.get_falla_por_cita(id_cita)
        if falla and self._is_mecanico_user():
            self.c_manage_diagnostico.set(falla.get("diagnostico") or "")
            self.c_manage_observaciones.set(falla.get("observaciones") or "")
            self.c_manage_solucion.set(falla.get("solucion") or "")
        if self.c_manage_mec_cb and cita.get("mecanico"):
            self.c_manage_mec_cb.set(cita["mecanico"])
        if self.c_manage_isla_cb and cita.get("isla"):
            self.c_manage_isla_cb.set(cita["isla"])

    def _update_cita_staff(self) -> None:
        try:
            sel = self.citas_tree.selection()
            if not sel:
                raise ValueError("Selecciona una cita de la lista.")
            id_cita = int(sel[0])
            cita = cita_service.get_cita_by_id(id_cita)
            if not cita:
                raise ValueError("Cita no encontrada.")
            if self._is_mecanico_user() and self.user:
                if cita.get("id_mecanico") != self.user["id"]:
                    raise ValueError("Solo puedes actualizar citas asignadas a ti.")

            estado = etiqueta_a_estado(self.c_manage_estado.get())
            if not estado:
                raise ValueError("Selecciona un estado válido.")

            updates: dict = {}
            if estado != "CANCELADA":
                updates["estado"] = estado
            if self._can_reassign_citas() and self.c_manage_mec_map:
                updates["id_mecanico"] = self._combo_id(
                    self.c_manage_mec_cb, self.c_manage_mec_map, "mecánico"
                )
            if self._can_reassign_citas() and self.c_manage_isla_map:
                updates["id_isla"] = self._combo_id(
                    self.c_manage_isla_cb, self.c_manage_isla_map, "isla"
                )

            if estado == "CANCELADA":
                if self._is_mecanico_user():
                    raise ValueError("Solo el administrador puede cancelar citas.")
                result = cita_service.cambiar_estado_cita(id_cita, estado)
            elif self._is_mecanico_user():
                result = cita_service.cambiar_estado_cita(id_cita, estado)
                falla_res = cita_service.actualizar_falla_cita(
                    id_cita,
                    diagnostico=self.c_manage_diagnostico.get().strip() or None,
                    observaciones=self.c_manage_observaciones.get().strip() or None,
                    solucion=self.c_manage_solucion.get().strip() or None,
                )
                if not falla_res.get("ok") and any([
                    self.c_manage_diagnostico.get().strip(),
                    self.c_manage_observaciones.get().strip(),
                    self.c_manage_solucion.get().strip(),
                ]):
                    raise ValueError(falla_res.get("error", "No se pudo guardar diagnóstico."))
            else:
                result = cita_service.update_cita(id_cita, updates)

            if not result.get("ok"):
                raise ValueError(result.get("error", "No se pudo actualizar la cita."))

            msg = "Estado actualizado." if self._is_mecanico_user() else "Cita actualizada. El cliente verá el nuevo estado y asignación."
            messagebox.showinfo("Citas", msg)
            self._load_citas()
            self._refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Citas", str(exc))

    def _reload_cita_form(self):
        if self._is_mecanico_user():
            return
        self._reload_cita_clientes()
        self._reload_cita_mecanicos()
        self._reload_cita_islas()
        self._reload_cita_servicios()
        self._reload_cita_horarios()

    def _reload_cita_clientes(self):
        if self._is_cliente_user():
            self._reload_cita_vehiculos()
            return
        if not self.c_cliente_cb:
            return
        clientes = catalog_service.list_clientes()
        self.c_cliente_map = self._fill_combo(
            self.c_cliente_cb,
            clientes,
            lambda c: f"{c['nombre']} — {c.get('telefono') or 'sin tel.'}",
            "id",
        )
        self._reload_cita_vehiculos()

    def _reload_cita_vehiculos(self):
        if not hasattr(self, "c_vehiculo_cb"):
            return
        try:
            if self._is_cliente_user():
                if not self.id_cliente:
                    raise ValueError("sin cliente")
                id_cliente = self.id_cliente
            else:
                id_cliente = self._combo_id(self.c_cliente_cb, self.c_cliente_map, "cliente")
        except ValueError:
            self.c_vehiculo_cb.set("")
            self.c_vehiculo_cb["values"] = ()
            self.c_vehiculo_map = {}
            return

        vehiculos = cita_service.list_vehiculos(id_cliente)
        self.c_vehiculo_map = self._fill_combo(
            self.c_vehiculo_cb,
            vehiculos,
            lambda v: f"{v['placa']} — {v['marca']} {v['modelo']}",
            "id",
        )

    def _reload_cita_horarios(self):
        fecha = self.c_fecha.get().strip()
        horarios = cita_service.list_horarios_disponibles(fecha, self.id_sucursal)
        if not horarios:
            self.c_horario_cb.set("")
            self.c_horario_cb["values"] = ("Sin horarios este día",)
            self.c_horario_cb.current(0)
            self.c_horario_map = {}
            return

        self.c_horario_map = self._fill_combo(
            self.c_horario_cb,
            horarios,
            lambda h: f"{str(h['hora'])[:8]} — disponible",
            "id",
        )

    def _reload_cita_mecanicos(self):
        if self._is_cliente_user() or not self.c_mecanico_cb:
            return
        mecanicos = cita_service.list_mecanicos(self.id_sucursal)
        self.c_mecanico_map = self._fill_combo(
            self.c_mecanico_cb,
            mecanicos,
            lambda m: m["nombre"],
            "id",
        )

    def _reload_cita_islas(self):
        if self._is_cliente_user() or not self.c_isla_cb:
            return
        islas = cita_service.list_islas(self.id_sucursal)
        self.c_isla_map = self._fill_combo(
            self.c_isla_cb,
            islas,
            lambda i: i["nombre"],
            "id",
        )

    def _reload_cita_servicios(self):
        servicios = catalog_service.list_tipos_mantenimiento(self.id_sucursal)
        self.c_servicio_rows = servicios
        self.c_servicios_lb.delete(0, tk.END)
        for s in servicios:
            self.c_servicios_lb.insert(tk.END, f"{s['nombre']} — ${s['precio']}")
        if servicios:
            self.c_servicios_lb.selection_set(0)

    def _save_cita(self):
        try:
            if not self.c_fallo.get().strip() or len(self.c_fallo.get().strip()) < 3:
                raise ValueError("Describe el fallo (mínimo 3 caracteres).")

            selected = self.c_servicios_lb.curselection()
            if not selected:
                raise ValueError("Selecciona al menos un tipo de mantenimiento.")
            servicios = [self.c_servicio_rows[i]["id"] for i in selected]

            horario_id = None
            fecha_cita = f"{self.c_fecha.get().strip()} 09:00:00"
            if self.c_horario_map:
                horario_id = self._combo_id(self.c_horario_cb, self.c_horario_map, "horario")
                h = next(
                    x for x in cita_service.list_horarios_disponibles(self.c_fecha.get().strip(), self.id_sucursal)
                    if x["id"] == horario_id
                )
                fecha_cita = f"{h['fecha']} {h['hora']}"
            elif self.c_horario_cb.get() == "Sin horarios este día":
                raise ValueError("No hay horarios disponibles para esa fecha.")

            if self._is_cliente_user():
                if not self.id_cliente:
                    raise ValueError("No se encontró tu ficha de cliente.")
                id_cliente = self.id_cliente
                defaults = cita_service.get_default_asignacion_taller(self.id_sucursal)
                id_mecanico = defaults["id_mecanico"]
                id_isla = defaults["id_isla"]
            else:
                id_cliente = self._combo_id(self.c_cliente_cb, self.c_cliente_map, "cliente")
                id_mecanico = self._combo_id(self.c_mecanico_cb, self.c_mecanico_map, "mecánico")
                id_isla = self._combo_id(self.c_isla_cb, self.c_isla_map, "isla")

            cita_id = cita_service.create_cita({
                "id_cliente": id_cliente,
                "id_vehiculo": self._combo_id(self.c_vehiculo_cb, self.c_vehiculo_map, "vehículo"),
                "id_sucursal": self.id_sucursal,
                "fecha_cita": fecha_cita,
                "id_horario": horario_id,
                "id_mecanico": id_mecanico,
                "id_isla": id_isla,
                "descripcion_fallo": self.c_fallo.get().strip(),
                "fecha_compromiso": self.c_fcomp.get().strip(),
                "hora_compromiso": self.c_hcomp.get().strip(),
            }, servicios)

            self.chat_service.rag.sync_fallas_from_db()
            msg = "Solicitud de cita enviada." if self._is_cliente_user() else "Cita creada correctamente."
            messagebox.showinfo("Citas", msg)
            self._load_citas()
            self._reload_cita_horarios()
            self.c_fallo.set("")
        except Exception as exc:
            messagebox.showerror("Citas", str(exc))

    def _load_citas(self):
        rows = cita_service.list_citas(**self._citas_filters())
        for r in rows:
            r["fecha_cita"] = str(r["fecha_cita"])
            r["descripcion_fallo"] = (r["descripcion_fallo"] or "")[:80]
            r["estado"] = estado_a_etiqueta(r.get("estado"))
        self._fill_tree(self.citas_tree, rows)

    def _nuevo_codigo_taller(self) -> None:
        from services.invitation_service import generar_codigo_aleatorio

        if hasattr(self, "taller_codigo"):
            self.taller_codigo.set(generar_codigo_aleatorio())

    def _guardar_codigo_taller(self) -> None:
        from services import invitation_service

        try:
            codigo = self.taller_codigo.get().strip()
            if not codigo:
                raise ValueError("Genera un código primero.")
            creado_por = self.user["id"] if self.user else None
            result = invitation_service.crear_codigo(
                self.id_sucursal,
                codigo=codigo,
                usos_maximos=50,
                creado_por=creado_por,
                permite_admin_sucursal=False,
            )
            if not result.get("ok"):
                raise ValueError(result.get("error", "No se pudo guardar el código."))
            messagebox.showinfo("Código guardado", f"Código de invitación: {result['codigo']}")
            self._nuevo_codigo_taller()
        except Exception as exc:
            messagebox.showerror("Código de invitación", str(exc))

    def _build_taller_tab(self):
        frame = ttk.Frame(padding=10)

        if can_manage_branch(self.user.get("rol_nombre") if self.user else None) and not self._is_super_admin_user():
            inv = ttk.LabelFrame(frame, text="Código de invitación de tu sucursal", padding=10)
            inv.pack(fill="x", pady=(0, 8))
            ttk.Label(
                inv,
                text=f"Sucursal: {self._sucursal_nombre()}",
                foreground=COLORS["muted"],
            ).pack(anchor="w", pady=(0, 6))
            self.taller_codigo = tk.StringVar()
            row = ttk.Frame(inv)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text="Código", width=14).pack(side="left")
            ttk.Entry(row, textvariable=self.taller_codigo, state="readonly", width=24).pack(side="left")
            ttk.Button(row, text="Generar código", command=self._nuevo_codigo_taller).pack(side="left", padx=8)
            ttk.Button(
                inv,
                text="Guardar código",
                style="Accent.TButton",
                command=self._guardar_codigo_taller,
            ).pack(anchor="e", pady=(4, 0))
            self._nuevo_codigo_taller()

        isla_form = ttk.LabelFrame(frame, text="Nueva isla", padding=10)
        isla_form.pack(fill="x")
        self.isla_nombre = tk.StringVar()
        row = ttk.Frame(isla_form)
        row.pack(fill="x")
        ttk.Label(row, text="Nombre isla", width=14).pack(side="left")
        ttk.Entry(row, textvariable=self.isla_nombre).pack(side="left", fill="x", expand=True)
        ttk.Button(isla_form, text="Crear isla", command=self._save_isla).pack(anchor="e", pady=4)

        asign_form = ttk.LabelFrame(frame, text="Asignar mecánico a isla", padding=10)
        asign_form.pack(fill="x", pady=8)
        self.asig_resp = tk.BooleanVar(value=False)
        self.asig_isla_map = {}
        self.asig_mec_map = {}
        self.asig_isla_cb = self._add_combo_row(asign_form, "Isla", width=20)
        self.asig_mec_cb = self._add_combo_row(asign_form, "Mecánico", width=20)
        self._reload_asignacion_combos()
        ttk.Checkbutton(asign_form, text="Es responsable", variable=self.asig_resp).pack(anchor="w")
        ttk.Button(asign_form, text="Asignar", command=self._assign_mecanico).pack(anchor="e", pady=4)

        self.islas_tree = self._make_tree(
            frame,
            ("nombre", "activo"),
            headers={"nombre": "Isla", "activo": "Activa"},
        )
        self._load_islas()
        return frame

    def _save_isla(self):
        try:
            cita_service.create_isla(self.isla_nombre.get().strip(), self.id_sucursal)
            messagebox.showinfo("Islas", "Isla creada.")
            self._load_islas()
            self._reload_asignacion_combos()
            if hasattr(self, "c_isla_cb"):
                self._reload_cita_islas()
        except Exception as exc:
            messagebox.showerror("Islas", str(exc))

    def _reload_asignacion_combos(self):
        if not hasattr(self, "asig_isla_cb"):
            return
        islas = cita_service.list_islas(self.id_sucursal)
        self.asig_isla_map = self._fill_combo(self.asig_isla_cb, islas, lambda i: i["nombre"], "id")
        mecanicos = cita_service.list_mecanicos(self.id_sucursal)
        self.asig_mec_map = self._fill_combo(self.asig_mec_cb, mecanicos, lambda m: m["nombre"], "id")

    def _assign_mecanico(self):
        try:
            cita_service.assign_mecanico_isla(
                self._combo_id(self.asig_isla_cb, self.asig_isla_map, "isla"),
                self._combo_id(self.asig_mec_cb, self.asig_mec_map, "mecánico"),
                self.asig_resp.get(),
            )
            messagebox.showinfo("Islas", "Mecánico asignado.")
        except Exception as exc:
            messagebox.showerror("Islas", str(exc))

    def _load_islas(self):
        self._fill_tree(self.islas_tree, cita_service.list_islas(self.id_sucursal))

    def _build_sucursales_tab(self):
        frame = ttk.Frame(padding=10)
        form = ttk.LabelFrame(frame, text="Nueva sucursal (taller)", padding=10)
        form.pack(fill="x")

        self.suc_nombre = tk.StringVar()
        self.suc_dir = tk.StringVar()
        self.suc_codigo = tk.StringVar()

        for label, var in [("Nombre", self.suc_nombre), ("Dirección", self.suc_dir)]:
            row = ttk.Frame(form)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Código invitación", width=14).pack(side="left")
        ttk.Entry(row, textvariable=self.suc_codigo, state="readonly", width=24).pack(side="left")

        actions = ttk.Frame(form)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Generar código", command=self._nuevo_codigo_sucursal).pack(side="right", padx=(8, 0))
        ttk.Button(
            actions,
            text="Crear sucursal",
            style="Accent.TButton",
            command=self._save_sucursal,
        ).pack(side="right")

        ttk.Label(
            frame,
            text="Genera un código, créala cuando te guste, y al guardar la sucursal se almacena ese código.",
            foreground=COLORS["muted"],
            wraplength=720,
        ).pack(anchor="w", pady=(8, 4))

        self.sucursales_tree = self._make_tree(
            frame,
            ("nombre", "direccion", "activo"),
            headers={"nombre": "Nombre", "direccion": "Dirección", "activo": "Activa"},
            height=10,
        )
        self._nuevo_codigo_sucursal()
        self._load_sucursales()
        return frame

    def _nuevo_codigo_sucursal(self) -> None:
        from services.invitation_service import generar_codigo_aleatorio

        if hasattr(self, "suc_codigo"):
            self.suc_codigo.set(generar_codigo_aleatorio())

    def _save_sucursal(self):
        from services import invitation_service

        try:
            nombre = self.suc_nombre.get().strip()
            if not nombre:
                raise ValueError("Indica el nombre de la sucursal.")
            codigo = self.suc_codigo.get().strip()
            if not codigo:
                raise ValueError("Genera un código de invitación antes de crear la sucursal.")

            id_sucursal = catalog_service.create_sucursal(nombre, self.suc_dir.get().strip())
            creado_por = self.user["id"] if self.user else None
            result = invitation_service.crear_codigo(
                id_sucursal,
                codigo=codigo,
                usos_maximos=50,
                creado_por=creado_por,
                permite_admin_sucursal=True,
            )
            if not result.get("ok"):
                raise ValueError(result.get("error", "Sucursal creada pero falló el código."))

            messagebox.showinfo(
                "Sucursales",
                f"Sucursal creada.\nCódigo de invitación: {result['codigo']}",
            )
            self.suc_nombre.set("")
            self.suc_dir.set("")
            self._nuevo_codigo_sucursal()
            self._load_sucursales()
        except Exception as exc:
            messagebox.showerror("Sucursales", str(exc))

    def _load_sucursales(self):
        rows = catalog_service.list_sucursales()
        for r in rows:
            r["activo"] = "Sí" if r.get("activo", 1) else "No"
        self._fill_tree(self.sucursales_tree, rows)

    def _build_usuarios_tab(self):
        frame = ttk.Frame(padding=10)
        form = ttk.LabelFrame(frame, text="Nuevo usuario del taller", padding=10)
        form.pack(fill="x")

        ttk.Label(
            form,
            text=(
                "El ROL define los permisos en el sistema. El PUESTO es solo el cargo en el taller "
                "(Gerente, Mecánico, etc.) y no cambia lo que puede hacer en la app."
            ),
            foreground=COLORS["muted"],
            wraplength=640,
        ).pack(anchor="w", pady=(0, 8))

        self.u_nombre = tk.StringVar()
        self.u_email = tk.StringVar()
        self.u_pass = tk.StringVar(value="pass1234")
        self.u_rol_map = {}
        self.u_suc_map = {}
        self.u_puesto_map = {}
        self.u_roles_staff = []

        for label, var in [("Nombre", self.u_nombre), ("Email", self.u_email), ("Contraseña", self.u_pass)]:
            row = ttk.Frame(form)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=var, show="*" if "Contraseña" in label else "").pack(side="left", fill="x", expand=True)

        self.u_rol_cb = self._add_combo_row(form, "Rol (permisos)", width=14)
        self.u_suc_cb = self._add_combo_row(form, "Sucursal", width=14)
        self.u_puesto_cb = self._add_combo_row(form, "Puesto en el taller", width=14)

        self.u_roles_staff = [r for r in catalog_service.list_roles() if r["nombre"] not in ("PENDIENTE",)]
        if not is_super_admin(self.user.get("rol_nombre") if self.user else None):
            self.u_roles_staff = [r for r in self.u_roles_staff if r["nombre"] != "SUPER_ADMIN"]
        self.u_rol_map = self._fill_combo(self.u_rol_cb, self.u_roles_staff, lambda r: r["nombre"], "id")
        sucursales = catalog_service.list_sucursales()
        self.u_suc_map = self._fill_combo(self.u_suc_cb, sucursales, lambda s: s["nombre"], "id")
        puestos = catalog_service.list_puestos()
        self.u_puesto_map = self._fill_combo(self.u_puesto_cb, puestos, lambda p: p["nombre"], "id")

        ttk.Label(
            form,
            text="Ej.: rol ADMIN + puesto Mecánico = administra la sucursal pero es mecánico de oficio.",
            foreground=COLORS["muted"],
            wraplength=640,
        ).pack(anchor="w", pady=(2, 0))
        ttk.Button(form, text="Guardar usuario", command=self._save_usuario).pack(anchor="e", pady=4)

        assign = ttk.LabelFrame(frame, text="Cambiar rol o puesto de usuario existente", padding=10)
        assign.pack(fill="x", pady=(0, 8))
        self.u_assign_map = {}
        self.u_assign_rol_map = {}
        self.u_assign_puesto_map = {}
        self.u_assign_cb = self._add_combo_row(assign, "Usuario", width=14)
        self.u_assign_rol_cb = self._add_combo_row(assign, "Rol (permisos)", width=14)
        self.u_assign_puesto_cb = self._add_combo_row(assign, "Puesto en el taller", width=14)
        ttk.Button(assign, text="Actualizar", command=self._assign_usuario_rol).pack(anchor="e", pady=6)
        self._reload_usuario_assign_combos()

        self.users_tree = self._make_tree(
            frame,
            ("nombre", "email", "rol", "puesto", "sucursal"),
            headers={
                "nombre": "Nombre", "email": "Email", "rol": "Rol (permisos)",
                "puesto": "Puesto", "sucursal": "Sucursal",
            },
        )
        self._load_usuarios()
        return frame

    def _reload_usuario_assign_combos(self):
        if not hasattr(self, "u_assign_cb"):
            return
        id_sucursal = None if self._is_super_admin_user() else self.id_sucursal
        usuarios = catalog_service.list_usuarios(id_sucursal)
        self.u_assign_map = self._fill_combo(
            self.u_assign_cb,
            usuarios,
            lambda u: f"{u['nombre']} — {u['email']} ({u['rol']})",
            "id",
        )
        roles = [r for r in catalog_service.list_roles() if r["nombre"] != "PENDIENTE"]
        if not self._is_super_admin_user():
            roles = [r for r in roles if r["nombre"] != "SUPER_ADMIN"]
        self.u_assign_rol_map = self._fill_combo(
            self.u_assign_rol_cb, roles, lambda r: r["nombre"], "id",
        )
        puestos = catalog_service.list_puestos()
        self.u_assign_puesto_map = self._fill_combo(
            self.u_assign_puesto_cb, puestos, lambda p: p["nombre"], "id",
        )

    def _assign_usuario_rol(self):
        try:
            id_usuario = self._combo_id(self.u_assign_cb, self.u_assign_map, "usuario")
            id_rol = self._combo_id(self.u_assign_rol_cb, self.u_assign_rol_map, "rol")
            rol_nombre = self.u_assign_rol_cb.get().strip()
            catalog_service.update_usuario_rol(id_usuario, id_rol, rol_nombre)
            if self.u_assign_puesto_cb.get().strip():
                id_puesto = self._combo_id(
                    self.u_assign_puesto_cb, self.u_assign_puesto_map, "puesto"
                )
                catalog_service.update_usuario_puesto(id_usuario, id_puesto)
            messagebox.showinfo("Usuarios", "Usuario actualizado.")
            self._load_usuarios()
            self._reload_usuario_assign_combos()
        except Exception as exc:
            messagebox.showerror("Usuarios", str(exc))

    def _save_usuario(self):
        from services.password_policy import normalize_password, validate_password

        try:
            email = self.u_email.get().strip()
            password = normalize_password(self.u_pass.get())
            ok, msg = validate_password(password, email)
            if not ok:
                messagebox.showerror("Usuarios", msg)
                return

            puesto_sel = self.u_puesto_cb.get()
            id_puesto = self.u_puesto_map.get(puesto_sel)
            catalog_service.create_usuario({
                "nombre": self.u_nombre.get().strip(),
                "email": email,
                "password": password,
                "id_rol": self._combo_id(self.u_rol_cb, self.u_rol_map, "rol"),
                "id_sucursal": self._combo_id(self.u_suc_cb, self.u_suc_map, "sucursal"),
                "id_puesto": id_puesto,
            })
            messagebox.showinfo("Usuarios", "Usuario creado.")
            self._load_usuarios()
            self._reload_cliente_usuarios()
        except Exception as exc:
            messagebox.showerror("Usuarios", str(exc))

    def _load_usuarios(self):
        id_sucursal = None if self._is_super_admin_user() else self.id_sucursal
        rows = catalog_service.list_usuarios(id_sucursal)
        for r in rows:
            r["puesto"] = r.get("puesto") or "—"
        self._fill_tree(self.users_tree, rows)

    @staticmethod
    def _add_combo_row(parent, label, width=26):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, width=width).pack(side="left")
        combo = ttk.Combobox(row, state="readonly")
        combo.pack(side="left", fill="x", expand=True)
        return combo

    @staticmethod
    def _fill_combo(combo, rows, label_fn, id_key="id"):
        mapping = {}
        labels = []
        for row in rows:
            text = label_fn(row)
            mapping[text] = row[id_key]
            labels.append(text)
        combo["values"] = labels
        if labels:
            combo.current(0)
        else:
            combo.set("")
        return mapping

    @staticmethod
    def _combo_id(combo, mapping, field_name):
        value = combo.get()
        if not value or value not in mapping:
            raise ValueError(f"Selecciona un {field_name} válido.")
        return mapping[value]

    @staticmethod
    def _make_tree(parent, columns, headers=None, height=12):
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=height)
        headers = headers or {}
        for col in columns:
            tree.heading(col, text=headers.get(col, col.replace("_", " ").title()))
            tree.column(col, width=130, anchor="w")
        tree.pack(fill="both", expand=True, pady=8)
        return tree

    @staticmethod
    def _fill_tree(tree, rows):
        tree.delete(*tree.get_children())
        if not rows:
            return
        cols = tree["columns"]
        for row in rows:
            values = [row.get(c, "") for c in cols]
            if row.get("id") is not None:
                tree.insert("", "end", iid=str(row["id"]), values=values)
            else:
                tree.insert("", "end", values=values)
