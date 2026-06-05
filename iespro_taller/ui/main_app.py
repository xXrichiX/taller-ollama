import tkinter as tk
from tkinter import messagebox, ttk

from config import DEFAULT_SUCURSAL_ID
from services import catalog_service, cita_service
from services.chat_service import ChatService
from ui.chat_window import ChatWindow
from ui.login_window import LoginWindow
from ui.theme import COLORS, apply_theme, style_listbox


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_theme(self)
        self.title("IESPRO-Taller")
        self.geometry("1180x760")
        self.minsize(1000, 650)

        self.user = None
        self.id_sucursal = DEFAULT_SUCURSAL_ID
        self.chat_service = ChatService(self.id_sucursal)
        self.chat_window = None

        self.status_var = tk.StringVar(value="Iniciando...")
        ttk.Label(self, textvariable=self.status_var, style="Status.TLabel", anchor="w").pack(side="bottom", fill="x", ipady=4)

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self._init_db()
        LoginWindow(self, self._on_login)
    def _init_db(self):
        from db.init_db import ensure_data_dir, init_database

        ensure_data_dir()
        ok, msg = init_database()
        self.status_var.set(msg if ok else f"BD: {msg}")

        if ok:
            rag_ok, rag_msg = self.chat_service.bootstrap()
            self.status_var.set(f"{msg} | {rag_msg if rag_ok else 'RAG: ' + rag_msg}")

    def _on_login(self, user):
        self.user = user
        if user.get("id_sucursal"):
            self.id_sucursal = user["id_sucursal"]
            self.chat_service.id_sucursal = self.id_sucursal

        for w in self.container.winfo_children():
            w.destroy()

        sucursal_nombre = self._sucursal_nombre()

        header = ttk.Frame(self.container, style="Header.TFrame", padding=(16, 12))
        header.pack(fill="x")

        left = ttk.Frame(header, style="Header.TFrame")
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="IESPRO-Taller", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            left,
            text=f"{user['nombre']}  ·  {user['rol_nombre']}  ·  {sucursal_nombre}",
            style="SubHeader.TLabel",
        ).pack(anchor="w")

        chat_btn = tk.Button(
            header,
            text="  Abrir asistente IA  ",
            bg=COLORS["accent"],
            fg="white",
            activebackground=COLORS["accent_hover"],
            activeforeground="white",
            relief="flat",
            font=("Helvetica", 11, "bold"),
            padx=12,
            pady=8,
            cursor="hand2",
            command=self._open_chat,
        )
        chat_btn.pack(side="right")

        notebook = ttk.Notebook(self.container)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        notebook.add(self._build_dashboard_tab(), text="  Inicio  ")
        notebook.add(self._build_clientes_tab(), text="  Clientes  ")
        notebook.add(self._build_vehiculos_tab(), text="  Vehículos  ")
        notebook.add(self._build_citas_tab(), text="  Citas  ")
        notebook.add(self._build_taller_tab(), text="  Mi Taller  ")
        notebook.add(self._build_usuarios_tab(), text="  Usuarios  ")

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
        self.chat_window = ChatWindow(self, self.chat_service)
    def _build_dashboard_tab(self):
        frame = ttk.Frame(padding=12)

        header_row = ttk.Frame(frame)
        header_row.pack(fill="x", pady=(0, 12))
        ttk.Label(header_row, text="Panel del taller", font=("Helvetica", 16, "bold")).pack(side="left")
        ttk.Button(header_row, text="Actualizar", command=self._refresh_dashboard).pack(side="right")

        self.dash_cards = ttk.Frame(frame)
        self.dash_cards.pack(fill="x", pady=(0, 12))

        self.dash_db_var = tk.StringVar(value="MySQL: comprobando...")
        db_outer = tk.Frame(frame, bg=COLORS["border"], padx=1, pady=1)
        db_outer.pack(fill="x", pady=(0, 12))
        db_bar = tk.Frame(db_outer, bg=COLORS["card"], padx=12, pady=8)
        db_bar.pack(fill="x")
        tk.Label(db_bar, textvariable=self.dash_db_var, bg=COLORS["card"], fg=COLORS["text"], font=("Helvetica", 10)).pack(anchor="w")

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
            height=14,
        )

        self._refresh_dashboard()
        return frame

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
        from db.connection import test_connection

        ok, db_msg = test_connection()
        citas = cita_service.list_citas(self.id_sucursal)
        islas = cita_service.list_islas(self.id_sucursal)
        clientes = catalog_service.list_clientes()
        vehiculos = cita_service.list_vehiculos()
        mecanicos = cita_service.list_mecanicos(self.id_sucursal)

        pendientes = sum(1 for c in citas if c["estado"] == "PENDIENTE")
        en_proceso = sum(1 for c in citas if c["estado"] == "EN_PROCESO")
        completadas = sum(1 for c in citas if c["estado"] == "COMPLETADA")

        if not hasattr(self, "dash_stat_vars"):
            self.dash_stat_vars = {
                "clientes": tk.StringVar(value="0"),
                "vehiculos": tk.StringVar(value="0"),
                "citas": tk.StringVar(value="0"),
                "pendientes": tk.StringVar(value="0"),
                "proceso": tk.StringVar(value="0"),
                "mecanicos": tk.StringVar(value="0"),
            }
            for w in self.dash_cards.winfo_children():
                w.destroy()
            row1 = ttk.Frame(self.dash_cards)
            row1.pack(fill="x")
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

        self.dash_stat_vars["clientes"].set(str(len(clientes)))
        self.dash_stat_vars["vehiculos"].set(str(len(vehiculos)))
        self.dash_stat_vars["citas"].set(str(len(citas)))
        self.dash_stat_vars["pendientes"].set(str(pendientes))
        self.dash_stat_vars["proceso"].set(str(en_proceso))
        self.dash_stat_vars["completadas"].set(str(completadas))
        self.dash_stat_vars["islas"].set(str(len(islas)))
        self.dash_stat_vars["mecanicos"].set(str(len(mecanicos)))

        self.dash_db_var.set(
            f"MySQL: {'Conectado' if ok else 'Error'} — {db_msg}  ·  Sucursal {self.id_sucursal}: {self._sucursal_nombre()}"
        )

        rows = []
        for c in citas[:12]:
            rows.append({
                "cliente": c["cliente"],
                "placa": c["placa"],
                "estado": c["estado"],
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
        opciones = [{"id": None, "nombre": "— Sin usuario —", "email": ""}] + [
            {"id": u["id"], "nombre": u["nombre"], "email": u["email"]} for u in usuarios
        ]
        self.cli_usuario_map = self._fill_combo(
            self.cli_usuario_cb,
            opciones,
            lambda u: u["nombre"] if u["id"] else "— Sin usuario —",
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
        form = ttk.LabelFrame(frame, text="Registrar vehículo", padding=10)
        form.pack(fill="x")

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

        self.v_cliente_cb = self._add_combo_row(form, "Propietario (cliente)", width=18)
        self.v_marca_cb = self._add_combo_row(form, "Marca", width=18)
        self.v_comb_cb = self._add_combo_row(form, "Tipo combustible", width=18)
        self.v_unidad_cb = self._add_combo_row(form, "Tipo unidad", width=18)

        self._reload_vehiculo_combos()
        ttk.Button(form, text="Guardar vehículo", command=self._save_vehiculo).pack(anchor="e", pady=6)

        self.veh_tree = self._make_tree(
            frame,
            ("placa", "marca", "modelo", "cliente", "numero_economico", "kilometraje"),
            headers={
                "placa": "Placa", "marca": "Marca", "modelo": "Modelo",
                "cliente": "Cliente", "numero_economico": "No. económico", "kilometraje": "Km",
            },
        )
        self._load_vehiculos()
        return frame

    def _reload_vehiculo_combos(self):
        clientes = catalog_service.list_clientes()
        self.v_cliente_map = self._fill_combo(
            self.v_cliente_cb,
            clientes,
            lambda c: f"{c['nombre']} — {c.get('telefono') or c.get('email') or 'sin contacto'}",
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
            id_cliente = self._combo_id(self.v_cliente_cb, self.v_cliente_map, "cliente")
            cliente = next(c for c in catalog_service.list_clientes() if c["id"] == id_cliente)
            if not cliente.get("id_usuario"):
                raise ValueError("El cliente seleccionado no tiene usuario vinculado.")

            cita_service.create_vehiculo({
                "numero_economico": self.v_num.get().strip(),
                "placa": self.v_placa.get().strip(),
                "serie": self.v_serie.get().strip(),
                "modelo": self.v_modelo.get().strip(),
                "kilometraje": int(self.v_km.get()),
                "dias_mantenimiento": int(self.v_dias.get()),
                "observaciones": self.v_obs.get().strip() or None,
                "id_cliente": id_cliente,
                "id_usuario": cliente["id_usuario"],
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
        self._fill_tree(self.veh_tree, cita_service.list_vehiculos())

    def _build_citas_tab(self):
        frame = ttk.Frame(padding=10)
        form = ttk.LabelFrame(frame, text="Nueva cita", padding=10)
        form.pack(fill="x")

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

        self.c_cliente_cb = self._add_combo_row(form, "Cliente")
        self.c_vehiculo_cb = self._add_combo_row(form, "Vehículo")
        self.c_cliente_cb.bind("<<ComboboxSelected>>", lambda e: self._reload_cita_vehiculos())

        row = ttk.Frame(form)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Fecha cita", width=26).pack(side="left")
        ttk.Entry(row, textvariable=self.c_fecha, width=14).pack(side="left")
        ttk.Button(row, text="Cargar horarios", command=self._reload_cita_horarios).pack(side="left", padx=8)

        self.c_horario_cb = self._add_combo_row(form, "Hora de la cita")
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

        ttk.Button(form, text="Crear cita", command=self._save_cita).pack(anchor="e", pady=6)

        self._reload_cita_form()

        self.citas_tree = self._make_tree(
            frame,
            ("cliente", "placa", "fecha_cita", "estado", "mecanico", "isla", "descripcion_fallo"),
            headers={
                "cliente": "Cliente", "placa": "Placa", "fecha_cita": "Fecha",
                "estado": "Estado", "mecanico": "Mecánico", "isla": "Isla",
                "descripcion_fallo": "Falla reportada",
            },
        )
        self._load_citas()
        return frame

    def _reload_cita_form(self):
        self._reload_cita_clientes()
        self._reload_cita_mecanicos()
        self._reload_cita_islas()
        self._reload_cita_servicios()
        self._reload_cita_horarios()

    def _reload_cita_clientes(self):
        clientes = catalog_service.list_clientes()
        self.c_cliente_map = self._fill_combo(
            self.c_cliente_cb,
            clientes,
            lambda c: f"{c['nombre']} — {c.get('telefono') or 'sin tel.'}",
            "id",
        )
        self._reload_cita_vehiculos()

    def _reload_cita_vehiculos(self):
        if not hasattr(self, "c_cliente_cb"):
            return
        try:
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
        mecanicos = cita_service.list_mecanicos(self.id_sucursal)
        self.c_mecanico_map = self._fill_combo(
            self.c_mecanico_cb,
            mecanicos,
            lambda m: m["nombre"],
            "id",
        )

    def _reload_cita_islas(self):
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

            cita_id = cita_service.create_cita({
                "id_cliente": self._combo_id(self.c_cliente_cb, self.c_cliente_map, "cliente"),
                "id_vehiculo": self._combo_id(self.c_vehiculo_cb, self.c_vehiculo_map, "vehículo"),
                "id_sucursal": self.id_sucursal,
                "fecha_cita": fecha_cita,
                "id_horario": horario_id,
                "id_mecanico": self._combo_id(self.c_mecanico_cb, self.c_mecanico_map, "mecánico"),
                "id_isla": self._combo_id(self.c_isla_cb, self.c_isla_map, "isla"),
                "descripcion_fallo": self.c_fallo.get().strip(),
                "fecha_compromiso": self.c_fcomp.get().strip(),
                "hora_compromiso": self.c_hcomp.get().strip(),
            }, servicios)

            self.chat_service.rag.sync_fallas_from_db()
            messagebox.showinfo("Citas", f"Cita creada correctamente.")
            self._load_citas()
            self._reload_cita_horarios()
            self.c_fallo.set("")
        except Exception as exc:
            messagebox.showerror("Citas", str(exc))

    def _load_citas(self):
        rows = cita_service.list_citas(self.id_sucursal)
        for r in rows:
            r["fecha_cita"] = str(r["fecha_cita"])
            r["descripcion_fallo"] = (r["descripcion_fallo"] or "")[:80]
        self._fill_tree(self.citas_tree, rows)

    def _build_taller_tab(self):
        frame = ttk.Frame(padding=10)

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

    def _build_usuarios_tab(self):
        frame = ttk.Frame(padding=10)
        form = ttk.LabelFrame(frame, text="Nuevo usuario", padding=10)
        form.pack(fill="x")

        self.u_nombre = tk.StringVar()
        self.u_email = tk.StringVar()
        self.u_pass = tk.StringVar(value="pass123")
        self.u_es_cli = tk.BooleanVar(value=False)
        self.u_es_tra = tk.BooleanVar(value=True)
        self.u_rol_map = {}
        self.u_suc_map = {}
        self.u_puesto_map = {}

        for label, var in [("Nombre", self.u_nombre), ("Email", self.u_email), ("Contraseña", self.u_pass)]:
            row = ttk.Frame(form)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=14).pack(side="left")
            ttk.Entry(row, textvariable=var, show="*" if "Contraseña" in label else "").pack(side="left", fill="x", expand=True)

        self.u_rol_cb = self._add_combo_row(form, "Rol", width=14)
        self.u_suc_cb = self._add_combo_row(form, "Sucursal", width=14)
        self.u_puesto_cb = self._add_combo_row(form, "Puesto (opcional)", width=14)

        roles = catalog_service.list_roles()
        self.u_rol_map = self._fill_combo(self.u_rol_cb, roles, lambda r: r["nombre"], "id")
        sucursales = catalog_service.list_sucursales()
        self.u_suc_map = self._fill_combo(self.u_suc_cb, sucursales, lambda s: s["nombre"], "id")
        puestos = [{"id": None, "nombre": "— Sin puesto —"}] + catalog_service.list_puestos()
        self.u_puesto_map = self._fill_combo(
            self.u_puesto_cb, puestos,
            lambda p: p["nombre"] if p["id"] else "— Sin puesto —", "id",
        )

        ttk.Checkbutton(form, text="Es cliente", variable=self.u_es_cli).pack(anchor="w", pady=2)
        ttk.Checkbutton(form, text="Es trabajador", variable=self.u_es_tra).pack(anchor="w")
        ttk.Button(form, text="Guardar usuario", command=self._save_usuario).pack(anchor="e", pady=8)

        self.users_tree = self._make_tree(
            frame,
            ("nombre", "email", "rol", "sucursal", "es_cliente", "es_trabajador"),
            headers={
                "nombre": "Nombre", "email": "Email", "rol": "Rol", "sucursal": "Sucursal",
                "es_cliente": "Cliente", "es_trabajador": "Trabajador",
            },
        )
        self._load_usuarios()
        return frame

    def _save_usuario(self):
        try:
            puesto_sel = self.u_puesto_cb.get()
            id_puesto = self.u_puesto_map.get(puesto_sel)
            catalog_service.create_usuario({
                "nombre": self.u_nombre.get().strip(),
                "email": self.u_email.get().strip(),
                "password": self.u_pass.get().strip(),
                "id_rol": self._combo_id(self.u_rol_cb, self.u_rol_map, "rol"),
                "id_sucursal": self._combo_id(self.u_suc_cb, self.u_suc_map, "sucursal"),
                "es_cliente": int(self.u_es_cli.get()),
                "es_trabajador": int(self.u_es_tra.get()),
                "id_puesto": id_puesto if id_puesto else None,
            })
            messagebox.showinfo("Usuarios", "Usuario creado.")
            self._load_usuarios()
            self._reload_cliente_usuarios()
        except Exception as exc:
            messagebox.showerror("Usuarios", str(exc))

    def _load_usuarios(self):
        self._fill_tree(self.users_tree, catalog_service.list_usuarios())

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
            tree.insert("", "end", values=values)
