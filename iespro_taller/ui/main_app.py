import tkinter as tk
from tkinter import messagebox, ttk

from config import DEFAULT_SUCURSAL_ID
from services import catalog_service, cita_service
from services.chat_service import ChatService
from services.estado_labels import ESTADOS_MECANICO_UI, ESTADOS_UI, estado_a_etiqueta, etiqueta_a_estado
from services.user_roles import (
    can_manage_branch,
    is_admin,
    is_cliente,
    is_mecanico,
    is_pending,
    is_staff_manager,
    is_workshop_staff,
)
from ui.chat_window import ChatWindow
from ui.login_window import LoginFrame
from ui.side_panel import SidePanelLayout
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

        LoginFrame(self.container, self._on_login)
        self.after_idle(self._init_db)

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
                "Un administrador debe asignarte tu puesto (Admin o Mecánico) "
                "antes de que puedas usar el sistema.",
            )
            return

        self.user = user
        self.id_cliente = None
        self.sucursales_ids = user.get("sucursales_ids") or []
        if is_cliente(user.get("rol_nombre")) and user.get("id"):
            cliente = catalog_service.get_cliente_by_usuario(user["id"])
            self.id_cliente = cliente["id"] if cliente else None
        if is_mecanico(user.get("rol_nombre")):
            if self.sucursales_ids:
                self.id_sucursal = self.sucursales_ids[0]
            elif user.get("id_sucursal"):
                self.id_sucursal = user["id_sucursal"]
            else:
                self.id_sucursal = None
        elif is_admin(user.get("rol_nombre")):
            sucursales = catalog_service.list_sucursales()
            self.sucursales_ids = [s["id"] for s in sucursales]
            self.id_sucursal = None
        elif user.get("id_sucursal"):
            self.id_sucursal = user["id_sucursal"]
        else:
            self.id_sucursal = None
        if self.id_sucursal:
            self.chat_service.id_sucursal = self.id_sucursal
        else:
            self.chat_service.id_sucursal = None
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

        if is_admin(user.get("rol_nombre")) or is_mecanico(user.get("rol_nombre")):
            notebook.add(self._build_sucursales_tab(), text="  Sucursales  ")

        if is_admin(user.get("rol_nombre")) or is_mecanico(user.get("rol_nombre")):
            notebook.add(self._build_clientes_tab(), text="  Clientes  ")

        if is_cliente(user.get("rol_nombre")):
            veh_label = "  Mis Vehículos  "
            cita_label = "  Mis Citas  "
        elif is_mecanico(user.get("rol_nombre")):
            veh_label = "  Vehículos  "
            cita_label = "  Citas  "
        else:
            veh_label = "  Vehículos  "
            cita_label = "  Citas  "

        if not is_cliente(user.get("rol_nombre")):
            notebook.add(self._build_vehiculos_tab(), text=veh_label)
        elif is_cliente(user.get("rol_nombre")):
            notebook.add(self._build_vehiculos_tab(), text=veh_label)

        notebook.add(self._build_citas_tab(), text=cita_label)

        if is_admin(user.get("rol_nombre")):
            notebook.add(self._build_usuarios_tab(), text="  Usuarios  ")

    def _build_header(self, user: dict, sucursal_nombre: str) -> None:
        header = tk.Frame(self.container, bg=COLORS["header"], padx=20, pady=10)
        header.pack(fill="x")

        left = tk.Frame(header, bg=COLORS["header"])
        left.pack(side="left", fill="x", expand=True)

        profile_row = tk.Frame(left, bg=COLORS["header"])
        profile_row.pack(anchor="w")

        self.user_menu = UserProfileMenu(
            profile_row,
            nombre=user["nombre"],
            rol=user["rol_nombre"],
            on_profile=self._show_profile,
            on_logout=self._logout,
        )
        self.user_menu.pack(side="left")

        if is_admin(user.get("rol_nombre")) or is_mecanico(user.get("rol_nombre")):
            self.sucursal_var = tk.StringVar()
            self.sucursal_cb = ttk.Combobox(
                profile_row,
                textvariable=self.sucursal_var,
                state="readonly",
                width=24,
                style="Header.TCombobox",
                font=("Helvetica", 11),
            )
            self.sucursal_cb.pack(side="left", padx=(18, 0), pady=8)
            self.sucursal_cb.bind("<<ComboboxSelected>>", self._on_sucursal_changed)
            self._reload_sucursal_selector()

        ttk.Button(
            header,
            text="Abrir asistente",
            style="Accent.TButton",
            command=self._open_chat,
        ).pack(side="right", pady=4)

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
            f"Puesto: {puesto}\n"
            f"Sucursal activa: {self._sucursal_nombre()}",
        )

    def _reload_sucursal_selector(self) -> None:
        if not hasattr(self, "sucursal_cb"):
            return
        if self._is_admin_user():
            rows = catalog_service.list_sucursales()
        elif self.user:
            rows = catalog_service.list_sucursales_usuario(self.user["id"])
        else:
            rows = []
        self._sucursal_map = {s["nombre"]: s["id"] for s in rows}
        names = list(self._sucursal_map.keys())
        self.sucursal_cb["values"] = names
        if self.id_sucursal:
            current = self._sucursal_nombre()
            if current in names:
                self.sucursal_var.set(current)
            elif names:
                self.sucursal_var.set(names[0])
                self._switch_sucursal(self._sucursal_map[names[0]])
            else:
                self.sucursal_var.set("— Sin sucursal —")
        else:
            self.sucursal_var.set("— Sin sucursal —")

    def _on_sucursal_changed(self, _event=None) -> None:
        nombre = self.sucursal_var.get()
        if nombre in ("", "— Sin sucursal —"):
            return
        if nombre and hasattr(self, "_sucursal_map") and nombre in self._sucursal_map:
            self._switch_sucursal(self._sucursal_map[nombre])

    def _switch_sucursal(self, id_sucursal: int) -> None:
        self.id_sucursal = id_sucursal
        self.chat_service.id_sucursal = id_sucursal
        if hasattr(self, "clientes_tree"):
            self._load_clientes()
        if hasattr(self, "veh_tree"):
            self._load_vehiculos()
        if hasattr(self, "citas_tree"):
            self._load_citas()
        if hasattr(self, "users_tree"):
            self._load_usuarios()
        if hasattr(self, "islas_tree"):
            self._load_islas()
        if hasattr(self, "sucursales_tree") and not self._is_admin_user():
            pass
        if hasattr(self, "dash_citas_tree"):
            self._refresh_dashboard()

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

    def _requires_sucursal_data(self) -> bool:
        return bool(
            self.user
            and (is_admin(self.user.get("rol_nombre")) or is_mecanico(self.user.get("rol_nombre")))
            and not self.id_sucursal
        )

    def _sucursal_nombre(self):
        if not self.id_sucursal:
            return "Sin sucursal"
        for s in catalog_service.list_sucursales():
            if s["id"] == self.id_sucursal:
                return s["nombre"]
        return f"Sucursal {self.id_sucursal}"

    def _require_sucursal(self) -> int:
        if not self.id_sucursal:
            raise ValueError("Selecciona o crea una sucursal primero.")
        return self.id_sucursal

    def _open_chat(self):
        if self.chat_window and self.chat_window.winfo_exists():
            self.chat_window.lift()
            self.chat_window.focus_force()
            return
        if not self.id_sucursal:
            messagebox.showinfo(
                "Asistente",
                "Selecciona una sucursal en el menú superior,\n"
                "o crea una en la pestaña Sucursales.",
            )
            return
        try:
            self.chat_service.id_sucursal = self.id_sucursal
            self.chat_service.ensure_conversation()
            self.chat_window = ChatWindow(self, self.chat_service)
        except Exception as exc:
            messagebox.showerror("Asistente", f"No se pudo abrir el asistente:\n{exc}")
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

    def _is_admin_user(self) -> bool:
        return bool(self.user and is_admin(self.user.get("rol_nombre")))

    def _is_cliente_user(self) -> bool:
        return bool(self.user and is_cliente(self.user.get("rol_nombre")))

    def _is_mecanico_user(self) -> bool:
        return bool(self.user and is_mecanico(self.user.get("rol_nombre")))

    def _citas_filters(self) -> dict:
        filters: dict = {}
        if self._is_cliente_user() and self.id_cliente:
            filters["id_cliente"] = self.id_cliente
        if self.id_sucursal:
            filters["id_sucursal"] = self.id_sucursal
        return filters

    def _clientes_filters(self) -> dict:
        if self.id_sucursal:
            return {"id_sucursal": self.id_sucursal}
        return {}

    def _can_reassign_citas(self) -> bool:
        return bool(self.user and can_manage_branch(self.user.get("rol_nombre")))

    def _can_manage_citas(self) -> bool:
        return bool(self.user and is_workshop_staff(self.user.get("rol_nombre")))

    def _can_create_citas(self) -> bool:
        return bool(
            self.user
            and (can_manage_branch(self.user.get("rol_nombre")) or is_mecanico(self.user.get("rol_nombre")))
        )

    def _can_create_clientes(self) -> bool:
        return bool(
            self.user
            and (can_manage_branch(self.user.get("rol_nombre")) or is_mecanico(self.user.get("rol_nombre")))
        )

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
        if self._requires_sucursal_data():
            citas: list = []
            vehiculos: list = []
            clientes: list = []
            islas: list = []
            mecanicos: list = []
        else:
            filters = self._citas_filters()
            citas = cita_service.list_citas(**filters)
            id_cliente = filters.get("id_cliente")
            vehiculos = []
            if id_cliente:
                vehiculos = cita_service.list_vehiculos(id_cliente=id_cliente)
            elif self._is_mecanico_user() and self.id_sucursal:
                vehiculos = cita_service.list_vehiculos(id_sucursal=self.id_sucursal)
            elif self._is_admin_user() and self.id_sucursal:
                vehiculos = cita_service.list_vehiculos(id_sucursal=self.id_sucursal)

            if self._is_cliente_user() or self._is_mecanico_user():
                clientes = []
                islas = []
                mecanicos = []
            elif self._is_admin_user():
                clientes = (
                    catalog_service.list_clientes(**self._clientes_filters())
                    if self.id_sucursal
                    else []
                )
                islas = cita_service.list_islas(self.id_sucursal) if self.id_sucursal else []
                mecanicos = cita_service.list_mecanicos(self.id_sucursal) if self.id_sucursal else []
            else:
                clientes = catalog_service.list_clientes(**self._clientes_filters())
                islas = cita_service.list_islas(self.id_sucursal) if self.id_sucursal else []
                mecanicos = cita_service.list_mecanicos(self.id_sucursal) if self.id_sucursal else []

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
                self._stat_card(row1, "Mis citas", self.dash_stat_vars["citas"], accent=True)
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
        self._cli_layout = SidePanelLayout(frame)
        self._cli_layout.frame().pack(fill="both", expand=True)
        self._cli_layout.add_toolbar_button("+ Crear cliente", self._open_cliente_create)

        self.cli_nombre = tk.StringVar()
        self.cli_tel = tk.StringVar()
        self.cli_email = tk.StringVar()
        self.cli_usuario_map = {}

        form = self._cli_layout.panel_form
        for label, var in [("Nombre", self.cli_nombre), ("Teléfono", self.cli_tel), ("Email", self.cli_email)]:
            row = ttk.Frame(form)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

        self.cli_usuario_cb = self._add_combo_row(form, "Usuario vinculado", width=14)
        ttk.Button(form, text="Guardar cliente", style="Accent.TButton", command=self._save_cliente).pack(
            anchor="e", pady=8
        )

        self.clientes_tree = self._make_tree(
            self._cli_layout.tree_host,
            ("nombre", "telefono", "email", "usuario_email"),
            headers={"nombre": "Nombre", "telefono": "Teléfono", "email": "Email", "usuario_email": "Usuario"},
            pady=0,
        )
        self._load_clientes()
        return frame

    def _open_cliente_create(self) -> None:
        self.cli_nombre.set("")
        self.cli_tel.set("")
        self.cli_email.set("")
        self._reload_cliente_usuarios()
        self._cli_layout.show("Nuevo cliente")

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
            if hasattr(self, "_cli_layout"):
                self._cli_layout.hide()
        except Exception as exc:
            messagebox.showerror("Clientes", str(exc))

    def _load_clientes(self):
        if self._requires_sucursal_data():
            self._fill_tree(self.clientes_tree, [])
            return
        self._fill_tree(self.clientes_tree, catalog_service.list_clientes(**self._clientes_filters()))

    def _build_vehiculos_tab(self):
        frame = ttk.Frame(padding=10)
        can_edit = self._can_create_citas() or self._is_cliente_user()

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
            self._veh_layout = SidePanelLayout(frame)
            self._veh_layout.frame().pack(fill="both", expand=True)
            btn_label = "+ Registrar mi vehículo" if self._is_cliente_user() else "+ Crear vehículo"
            self._veh_layout.add_toolbar_button(btn_label, self._open_vehiculo_create)

            form = self._veh_layout.panel_form
            form_title = "Registrar mi vehículo" if self._is_cliente_user() else "Registrar vehículo"

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
                if not self._is_mecanico_user():
                    self.v_mecanico_cb = self._add_combo_row(form, "Mecánico asignado", width=18)
            self.v_marca_cb = self._add_combo_row(form, "Marca", width=18)
            self.v_comb_cb = self._add_combo_row(form, "Tipo combustible", width=18)
            self.v_unidad_cb = self._add_combo_row(form, "Tipo unidad", width=18)

            ttk.Button(
                form, text="Guardar vehículo", style="Accent.TButton", command=self._save_vehiculo
            ).pack(anchor="e", pady=6)
            tree_host = self._veh_layout.tree_host
        else:
            layout = ttk.Frame(frame)
            layout.pack(fill="both", expand=True)
            tree_host = layout

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

        self.veh_tree = self._make_tree(tree_host, cols, headers=headers, pady=0 if can_edit else 8)
        self._load_vehiculos()
        return frame

    def _open_vehiculo_create(self) -> None:
        self.v_num.set("")
        self.v_placa.set("")
        self.v_serie.set("")
        self.v_modelo.set("")
        self.v_km.set("0")
        self.v_dias.set("90")
        self.v_obs.set("")
        self._reload_vehiculo_combos()
        title = "Registrar mi vehículo" if self._is_cliente_user() else "Nuevo vehículo"
        self._veh_layout.show(title)

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
            if self._is_mecanico_user() and self.user:
                id_mecanico = self.user["id"]
            elif self.v_mecanico_cb and self.v_mecanico_map:
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
            if hasattr(self, "_veh_layout"):
                self._veh_layout.hide()
        except Exception as exc:
            messagebox.showerror("Vehículos", str(exc))

    def _load_vehiculos(self):
        if self._requires_sucursal_data():
            rows = []
        elif self._is_cliente_user():
            rows = cita_service.list_vehiculos(id_cliente=self.id_cliente)
        elif self._is_mecanico_user() and self.id_sucursal:
            rows = cita_service.list_vehiculos(id_sucursal=self.id_sucursal)
        elif self._is_admin_user() and self.id_sucursal:
            rows = cita_service.list_vehiculos(id_sucursal=self.id_sucursal)
        else:
            rows = cita_service.list_vehiculos(id_sucursal=self.id_sucursal)
        self._fill_tree(self.veh_tree, rows)

    def _build_citas_tab(self):
        frame = ttk.Frame(padding=10)
        self._cita_layout = SidePanelLayout(frame, panel_width=440)
        self._cita_layout.frame().pack(fill="both", expand=True)

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
            btn_text = "+ Solicitar cita" if self._is_cliente_user() else "+ Crear cita"
            self._cita_layout.add_toolbar_button(btn_text, self._open_cita_create)

        self.c_crear_frame = ttk.Frame(self._cita_layout.panel_form)
        if self._can_create_citas() or self._is_cliente_user():
            form = self.c_crear_frame
            if self._can_create_citas():
                self.c_cliente_cb = self._add_combo_row(form, "Cliente")
                self.c_cliente_cb.bind("<<ComboboxSelected>>", lambda e: self._reload_cita_vehiculos())

            self.c_vehiculo_cb = self._add_combo_row(form, "Vehículo")

            row = ttk.Frame(form)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text="Fecha cita", width=26).pack(side="left")
            ttk.Entry(row, textvariable=self.c_fecha, width=14).pack(side="left")
            ttk.Button(row, text="Cargar horarios", command=self._reload_cita_horarios).pack(side="left", padx=8)

            self.c_horario_cb = self._add_combo_row(form, "Hora de la cita")
            if self._can_reassign_citas():
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

            save_text = "Solicitar cita" if self._is_cliente_user() else "Crear cita"
            ttk.Button(form, text=save_text, style="Accent.TButton", command=self._save_cita).pack(anchor="e", pady=6)

        self.c_manage_frame = ttk.Frame(self._cita_layout.panel_form)
        if self._can_manage_citas():
            manage = self.c_manage_frame
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
            ttk.Button(
                manage, text="Guardar cambios", style="Accent.TButton", command=self._update_cita_staff
            ).pack(anchor="e", pady=6)

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

        self.citas_tree = self._make_tree(
            self._cita_layout.tree_host, citas_cols, headers=citas_headers, pady=0
        )
        self.citas_tree.bind("<<TreeviewSelect>>", self._on_cita_selected)
        self._load_citas()
        return frame

    def _open_cita_create(self) -> None:
        self.c_fallo.set("")
        self.c_manage_frame.pack_forget()
        self.c_crear_frame.pack(fill="both", expand=True)
        self._reload_cita_form()
        title = "Solicitar cita" if self._is_cliente_user() else "Nueva cita"
        self._cita_layout.show(title)

    def _show_cita_manage_panel(self) -> None:
        self.c_crear_frame.pack_forget()
        self.c_manage_frame.pack(fill="both", expand=True)
        title = (
            "Actualizar estado de la cita"
            if self._is_mecanico_user()
            else "Actualizar cita seleccionada"
        )
        self._cita_layout.show(title)

    def _reload_cita_manage_combos(self):
        if not self._can_reassign_citas() or not hasattr(self, "c_manage_mec_cb") or not self.c_manage_mec_cb:
            return
        if not self.id_sucursal:
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
        self._show_cita_manage_panel()
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
            if hasattr(self, "_cita_layout"):
                self._cita_layout.hide()
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
        if not self.id_sucursal:
            self.c_horario_cb.set("")
            self.c_horario_cb["values"] = ()
            self.c_horario_map = {}
            return
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
        if not self.id_sucursal:
            self.c_mecanico_cb.set("")
            self.c_mecanico_cb["values"] = ()
            self.c_mecanico_map = {}
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
        if not self.id_sucursal:
            self.c_isla_cb.set("")
            self.c_isla_cb["values"] = ()
            self.c_isla_map = {}
            return
        islas = cita_service.list_islas(self.id_sucursal)
        self.c_isla_map = self._fill_combo(
            self.c_isla_cb,
            islas,
            lambda i: i["nombre"],
            "id",
        )

    def _reload_cita_servicios(self):
        if not self.id_sucursal:
            self.c_servicio_rows = []
            self.c_servicios_lb.delete(0, tk.END)
            return
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
                if self._is_mecanico_user() and self.user:
                    defaults = cita_service.get_default_asignacion_taller(self.id_sucursal)
                    id_mecanico = self.user["id"]
                    id_isla = defaults["id_isla"]
                else:
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
            if hasattr(self, "_cita_layout"):
                self._cita_layout.hide()
        except Exception as exc:
            messagebox.showerror("Citas", str(exc))

    def _load_citas(self):
        if self._requires_sucursal_data():
            rows = []
        else:
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
            self.taller_codigo.set("")
            if hasattr(self, "_taller_layout"):
                self._taller_layout.hide()
        except Exception as exc:
            messagebox.showerror("Código de invitación", str(exc))

    def _build_taller_tab(self):
        frame = ttk.Frame(padding=10)
        self._taller_layout = SidePanelLayout(frame)
        self._taller_layout.frame().pack(fill="both", expand=True)
        self._taller_layout.add_toolbar_button("+ Crear isla", self._open_isla_create)
        if can_manage_branch(self.user.get("rol_nombre") if self.user else None) and self._is_admin_user():
            self._taller_layout.add_toolbar_button("+ Código invitación", self._open_taller_codigo, accent=False)

        self.taller_isla_frame = ttk.Frame(self._taller_layout.panel_form)
        self.isla_nombre = tk.StringVar()
        self.isla_mec_map = {}
        row = ttk.Frame(self.taller_isla_frame)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Nombre isla", width=14).pack(side="left")
        ttk.Entry(row, textvariable=self.isla_nombre).pack(side="left", fill="x", expand=True)
        self.isla_mec_cb = self._add_combo_row(self.taller_isla_frame, "Mecánico", width=14)
        ttk.Button(
            self.taller_isla_frame, text="Crear isla", style="Accent.TButton", command=self._save_isla
        ).pack(anchor="e", pady=8)

        self.taller_codigo_frame = ttk.Frame(self._taller_layout.panel_form)
        self.taller_codigo = tk.StringVar()
        ttk.Label(
            self.taller_codigo_frame,
            text=f"Sucursal: {self._sucursal_nombre()}",
            foreground=COLORS["muted"],
        ).pack(anchor="w", pady=(0, 6))
        row = ttk.Frame(self.taller_codigo_frame)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Código", width=14).pack(side="left")
        ttk.Entry(row, textvariable=self.taller_codigo, state="readonly", width=24).pack(side="left")
        ttk.Button(row, text="Generar código", command=self._nuevo_codigo_taller).pack(side="left", padx=8)
        ttk.Button(
            self.taller_codigo_frame,
            text="Guardar código",
            style="Accent.TButton",
            command=self._guardar_codigo_taller,
        ).pack(anchor="e", pady=(4, 0))

        self.islas_tree = self._make_tree(
            self._taller_layout.tree_host,
            ("nombre", "activo"),
            headers={"nombre": "Isla", "activo": "Activa"},
            pady=0,
        )
        self._load_islas()
        return frame

    def _open_isla_create(self) -> None:
        self.isla_nombre.set("")
        self.taller_codigo_frame.pack_forget()
        self.taller_isla_frame.pack(fill="both", expand=True)
        self._reload_isla_mecanico_combo()
        self._taller_layout.show("Nueva isla")

    def _open_taller_codigo(self) -> None:
        self.taller_codigo.set("")
        self.taller_isla_frame.pack_forget()
        self.taller_codigo_frame.pack(fill="both", expand=True)
        self._taller_layout.show("Código de invitación")

    def _save_isla(self):
        try:
            id_sucursal = self._require_sucursal()
            nombre = self.isla_nombre.get().strip()
            if not nombre:
                raise ValueError("Indica el nombre de la isla.")
            id_isla = cita_service.create_isla(nombre, id_sucursal)
            sel = self.isla_mec_cb.get() if self.isla_mec_cb else ""
            id_mecanico = self.isla_mec_map.get(sel) if sel else None
            if id_mecanico:
                cita_service.assign_mecanico_isla(id_isla, id_mecanico)
            messagebox.showinfo("Islas", "Isla creada.")
            self._load_islas()
            if hasattr(self, "c_isla_cb"):
                self._reload_cita_islas()
            if hasattr(self, "_taller_layout"):
                self._taller_layout.hide()
        except Exception as exc:
            messagebox.showerror("Islas", str(exc))

    def _reload_isla_mecanico_combo(self) -> None:
        if not hasattr(self, "isla_mec_cb") or not self.isla_mec_cb:
            return
        if not self.id_sucursal:
            self.isla_mec_cb.set("")
            self.isla_mec_cb["values"] = ()
            self.isla_mec_map = {}
            return
        mecanicos = cita_service.list_mecanicos(self.id_sucursal)
        opciones = [{"id": None, "nombre": "— Sin asignar —"}] + mecanicos
        self.isla_mec_map = self._fill_combo(
            self.isla_mec_cb,
            opciones,
            lambda m: m["nombre"] if m.get("id") else "— Sin asignar —",
            "id",
        )

    def _load_islas(self):
        if not self.id_sucursal:
            self._fill_tree(self.islas_tree, [])
            return
        self._fill_tree(self.islas_tree, cita_service.list_islas(self.id_sucursal))

    def _build_sucursales_tab(self):
        frame = ttk.Frame(padding=10)
        self._suc_layout = SidePanelLayout(frame)
        self._suc_layout.frame().pack(fill="both", expand=True)

        self.suc_nombre = tk.StringVar()
        self.suc_dir = tk.StringVar()
        self.suc_codigo = tk.StringVar()

        if self._is_admin_user():
            self._suc_layout.add_toolbar_button("+ Crear sucursal", self._open_sucursal_create)
            form = self._suc_layout.panel_form
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

        self.sucursales_tree = self._make_tree(
            self._suc_layout.tree_host,
            ("nombre", "direccion", "activo"),
            headers={"nombre": "Nombre", "direccion": "Dirección", "activo": "Activa"},
            height=10,
            pady=0,
        )
        if not self._is_admin_user():
            self.sucursales_tree.bind("<<TreeviewSelect>>", self._on_sucursal_tree_select)
        self._load_sucursales()
        return frame

    def _on_sucursal_tree_select(self, _event=None) -> None:
        if self._is_admin_user():
            return
        sel = self.sucursales_tree.selection()
        if not sel:
            return
        self._switch_sucursal(int(sel[0]))
        if hasattr(self, "sucursal_var"):
            self.sucursal_var.set(self._sucursal_nombre())

    def _open_sucursal_create(self) -> None:
        self.suc_nombre.set("")
        self.suc_dir.set("")
        self.suc_codigo.set("")
        self._suc_layout.show("Nueva sucursal (taller)")

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
            self.suc_codigo.set("")
            self._load_sucursales()
            self._reload_sucursal_selector()
            if not self.id_sucursal:
                self._switch_sucursal(id_sucursal)
            self._suc_layout.hide()
        except Exception as exc:
            messagebox.showerror("Sucursales", str(exc))

    def _load_sucursales(self):
        if self._is_admin_user():
            rows = catalog_service.list_sucursales()
        elif self.user:
            rows = catalog_service.list_sucursales_usuario(self.user["id"])
        else:
            rows = []
        for r in rows:
            r["activo"] = "Sí" if r.get("activo", 1) else "No"
        self._fill_tree(self.sucursales_tree, rows)

    def _build_usuarios_tab(self):
        frame = ttk.Frame(padding=10)
        self._usr_layout = SidePanelLayout(frame, panel_width=420)
        self._usr_layout.frame().pack(fill="both", expand=True)
        self._usr_layout.add_toolbar_button("+ Crear usuario", self._open_usuario_create)

        self.u_editing_id = None
        self.u_nombre = tk.StringVar()
        self.u_email = tk.StringVar()
        self.u_pass = tk.StringVar()
        self.u_suc_map = {}
        self.u_puesto_map = {}
        self.u_sucursales_rows = []

        form = self._usr_layout.panel_form

        ttk.Label(form, text="Información básica", style="Section.TLabel").pack(anchor="w", pady=(0, 4))
        for label, var in [("Nombre", self.u_nombre), ("Email", self.u_email)]:
            row = ttk.Frame(form)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

        ttk.Label(form, text="Seguridad", style="Section.TLabel").pack(anchor="w", pady=(8, 4))
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Contraseña", width=14).pack(side="left")
        ttk.Entry(row, textvariable=self.u_pass, show="*").pack(side="left", fill="x", expand=True)

        self.u_puesto_cb = self._add_combo_row(form, "Puesto", width=14)

        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Sucursales", width=14).pack(side="left", anchor="n")
        lb_wrap = ttk.Frame(row)
        lb_wrap.pack(side="left", fill="x", expand=True)
        self.u_sucursales_lb = tk.Listbox(lb_wrap, selectmode=tk.EXTENDED, height=5, exportselection=False)
        style_listbox(self.u_sucursales_lb)
        self.u_sucursales_lb.pack(side="left", fill="x", expand=True)
        scroll = ttk.Scrollbar(lb_wrap, orient="vertical", command=self.u_sucursales_lb.yview)
        scroll.pack(side="right", fill="y")
        self.u_sucursales_lb.configure(yscrollcommand=scroll.set)

        puestos = catalog_service.list_puestos()
        self.u_puesto_map = self._fill_combo(self.u_puesto_cb, puestos, lambda p: p["nombre"], "id")
        self._reload_usuario_sucursales_list()

        btn_row = ttk.Frame(form)
        btn_row.pack(fill="x", pady=(12, 0))
        ttk.Button(
            btn_row, text="Guardar cambios", style="Accent.TButton", command=self._save_usuario_panel
        ).pack(side="right")

        self.users_tree = self._make_tree(
            self._usr_layout.tree_host,
            ("nombre", "email", "puesto", "sucursal"),
            headers={
                "nombre": "Nombre", "email": "Email",
                "puesto": "Puesto", "sucursal": "Sucursal",
            },
            pady=0,
        )
        self.users_tree.bind("<<TreeviewSelect>>", self._on_usuario_selected)
        self._load_usuarios()
        return frame

    def _open_usuario_create(self) -> None:
        self.u_editing_id = None
        self.u_nombre.set("")
        self.u_email.set("")
        self.u_pass.set("pass1234")
        self._reload_usuario_panel_combos()
        self._usr_layout.show("Nuevo usuario del taller")

    def _reload_usuario_panel_combos(self) -> None:
        if not hasattr(self, "u_puesto_cb"):
            return
        puestos = catalog_service.list_puestos()
        self.u_puesto_map = self._fill_combo(self.u_puesto_cb, puestos, lambda p: p["nombre"], "id")
        self._reload_usuario_sucursales_list()

    def _reload_usuario_sucursales_list(self) -> None:
        if not hasattr(self, "u_sucursales_lb"):
            return
        self.u_sucursales_rows = catalog_service.list_sucursales()
        self.u_sucursales_lb.delete(0, tk.END)
        for s in self.u_sucursales_rows:
            self.u_sucursales_lb.insert(tk.END, s["nombre"])

    def _get_selected_usuario_sucursales(self) -> list[int]:
        if not hasattr(self, "u_sucursales_lb"):
            return []
        if self.u_puesto_cb.get().strip().lower() == "admin":
            return []
        selected = self.u_sucursales_lb.curselection()
        return [self.u_sucursales_rows[i]["id"] for i in selected]

    def _on_usuario_selected(self, _event=None) -> None:
        sel = self.users_tree.selection()
        if not sel:
            return
        id_usuario = int(sel[0])
        usuarios = catalog_service.list_usuarios()
        usuario = next((u for u in usuarios if u["id"] == id_usuario), None)
        if not usuario:
            return
        self.u_editing_id = id_usuario
        self.u_nombre.set(usuario.get("nombre") or "")
        self.u_email.set(usuario.get("email") or "")
        self.u_pass.set("")
        if usuario.get("puesto") and usuario["puesto"] != "—":
            self.u_puesto_cb.set(usuario["puesto"])
        self.u_sucursales_lb.selection_clear(0, tk.END)
        asignadas = {s["id"] for s in catalog_service.list_sucursales_usuario(id_usuario)}
        for idx, s in enumerate(self.u_sucursales_rows):
            if s["id"] in asignadas:
                self.u_sucursales_lb.selection_set(idx)
        self._usr_layout.show("Detalles del usuario")

    def _save_usuario_panel(self) -> None:
        if self.u_editing_id:
            self._assign_usuario_rol_from_panel()
        else:
            self._save_usuario()

    def _assign_usuario_rol_from_panel(self) -> None:
        try:
            id_usuario = self.u_editing_id
            if not id_usuario:
                raise ValueError("Selecciona un usuario de la lista.")
            puesto_nombre = self.u_puesto_cb.get().strip()
            if not puesto_nombre:
                raise ValueError("Selecciona un puesto.")
            id_puesto = self._combo_id(self.u_puesto_cb, self.u_puesto_map, "puesto")
            sucursales = self._get_selected_usuario_sucursales()
            if puesto_nombre.lower() == "mecánico" and not sucursales:
                raise ValueError("Selecciona al menos una sucursal para el mecánico.")
            catalog_service.assign_usuario_staff(
                id_usuario, id_puesto, puesto_nombre, id_sucursales=sucursales or None,
            )
            messagebox.showinfo("Usuarios", "Usuario actualizado.")
            self._load_usuarios()
            self._usr_layout.hide()
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

            puesto_sel = self.u_puesto_cb.get().strip()
            if not puesto_sel:
                raise ValueError("Selecciona un puesto.")
            id_puesto = self._combo_id(self.u_puesto_cb, self.u_puesto_map, "puesto")
            sucursales = self._get_selected_usuario_sucursales()
            if puesto_sel.lower() == "mecánico" and not sucursales:
                raise ValueError("Selecciona al menos una sucursal para el mecánico.")
            id_usuario = catalog_service.create_usuario({
                "nombre": self.u_nombre.get().strip(),
                "email": email,
                "password": password,
                "puesto_nombre": puesto_sel,
                "id_sucursal": sucursales[0] if sucursales else None,
                "id_puesto": id_puesto,
            })
            if sucursales and puesto_sel.lower() == "mecánico":
                catalog_service.set_usuario_sucursales(id_usuario, sucursales)
            messagebox.showinfo("Usuarios", "Usuario creado.")
            self._load_usuarios()
            self._reload_cliente_usuarios()
            if hasattr(self, "_usr_layout"):
                self._usr_layout.hide()
        except Exception as exc:
            messagebox.showerror("Usuarios", str(exc))

    def _load_usuarios(self):
        if self._requires_sucursal_data():
            rows = []
        else:
            rows = catalog_service.list_usuarios(self.id_sucursal if self._is_admin_user() else None)
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
    def _make_tree(parent, columns, headers=None, height=12, pady=8):
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=height)
        headers = headers or {}
        for col in columns:
            tree.heading(col, text=headers.get(col, col.replace("_", " ").title()))
            tree.column(col, width=130, anchor="w")
        tree.pack(fill="both", expand=True, pady=pady)
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
