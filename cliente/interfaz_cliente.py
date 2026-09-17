"""Interfaz grafica del Cliente Operador - Plataforma de Telemetria.

Diseno Soft UI en tonos azules claros, con paneles solidos y legibles.
Cuando se pierde la conexion se conservan los ultimos datos recibidos, pero se
presentan en gris para indicar que ya no representan informacion en tiempo real.
"""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from logica_cliente import (
    Alert,
    ClienteError,
    ClienteOperador,
    DEFAULT_HOST,
    DEFAULT_PORT,
    NodeData,
    NodeSummary,
    ProtocolError,
    SystemStatus,
)

# ---------------------------------------------------------------------------
# Paleta de colores (Soft UI & Neumorfismo Simulado)
# ---------------------------------------------------------------------------
BG_APP = "#E3EBF3"       # Fondo azul claro principal
BG_PANEL = "#F0F5FA"     # Paneles (simula el vidrio esmerilado sólido)
BG_CARD = "#E3EBF3"      # Tarjetas Neumórficas (mismo fondo que la app)
BORDER_LIGHT = "#FFFFFF" # Borde claro (luz)
BORDER_DARK = "#C4D0DF"  # Borde oscuro (sombra)

TXT_PRIMARY = "#2D3748"  # Texto principal oscuro
TXT_MUTED = "#718096"    # Texto secundario/etiquetas
TXT_FAINT = "#A0AEC0"    # Texto deshabilitado/placeholder
TXT_STALE = "#94A3B8"    # Datos conservados después de una desconexión (Gris)

ACCENT = "#60A5FA"       # Azul para botón primario
SUCCESS = "#059669"      # Verde esmeralda oscuro (muy legible para ACTIVE)
WARNING = "#F6AD55"      # Naranja
DANGER = "#FC8181"       # Rojo suave

# Colores pastel para las tarjetas superiores (Soft UI)
TOP_CARD_COLORS = {
    "BLUE": "#A0C4FF",
    "GREEN": "#B9FBC0",
    "RED": "#FFADAD",
    "PURPLE": "#BDB2FF",
    "ORANGE": "#FFD6A5"
}

# Colores vibrantes distintos a los nodos para las métricas
METRIC_COLORS = {
    "TEMP": "#FF8A65",      # Naranja/Coral
    "HUM": "#4FC3F7",       # Azul brillante
    "ENERGY": "#FFD54F",    # Amarillo
    "VIBRATION": "#BA68C8", # Púrpura
}

METRIC_LABELS = {
    "TEMP": ("Temperatura", "°C"),
    "HUM": ("Humedad", "%"),
    "ENERGY": ("Energía", "W"),
    "VIBRATION": ("Vibración", "mm/s"),
}

ALERT_LABELS = {
    "TEMP_HIGH": "Temperatura Alta",
    "HUM_HIGH": "Humedad Alta",
    "ENERGY_HIGH": "Energía Alta",
    "VIBRATION_HIGH": "Vibración Alta",
}

AUTO_REFRESH_MS = 5000


class OperatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Panel de Operador")
        self.geometry("1280x780")
        self.minsize(1040, 640)
        self.configure(bg=BG_APP)

        self.cliente = ClienteOperador(DEFAULT_HOST, DEFAULT_PORT)
        self._task_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._auto_refresh = tk.BooleanVar(value=False)
        self._nodes_cache: list[NodeSummary] = []
        self._alerts_cache: list[Alert] = []
        self._selected_node_id: str | None = None
        self._last_success_time: str | None = None
        self._connected = False

        self._build_fonts()
        self._build_styles()
        self._build_layout()

        self.after(150, self._procesar_cola)
        self.after(300, lambda: self._lanzar_tarea("status", self.cliente.obtener_estado_sistema))
        self.after(300, lambda: self._lanzar_tarea("nodos", self.cliente.obtener_nodos))
        self.after(300, lambda: self._lanzar_tarea("alertas", self.cliente.obtener_alertas))
        
        self.update_idletasks()

    def _build_fonts(self) -> None:
        fuente_base = "Helvetica"
        self.font_title = tkfont.Font(family=fuente_base, size=24, weight="bold")
        self.font_subtitle = tkfont.Font(family=fuente_base, size=11)
        self.font_section = tkfont.Font(family=fuente_base, size=13, weight="bold")
        self.font_body = tkfont.Font(family=fuente_base, size=11)
        self.font_metric_value = tkfont.Font(family=fuente_base, size=26, weight="bold")
        self.font_metric_label = tkfont.Font(family=fuente_base, size=11)
        self.font_stat_value = tkfont.Font(family=fuente_base, size=22, weight="bold")

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#FFFFFF", 
            font=("Helvetica", 12, "bold"),
            padding=(18, 11),
            borderwidth=0,
            focuscolor=ACCENT
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#93C5FD"), ("pressed", "#3B82F6"), ("disabled", TXT_FAINT)],
        )

        style.configure(
            "Light.TEntry",
            fieldbackground=BG_PANEL,
            background=BG_PANEL,
            foreground=TXT_PRIMARY,
            insertcolor=TXT_PRIMARY,
            borderwidth=1,
            bordercolor=BORDER_DARK,
            lightcolor=BORDER_LIGHT,
            padding=10,
        )

        style.configure(
            "Light.TCheckbutton",
            background=BG_APP,
            foreground=TXT_MUTED,
            font=self.font_subtitle,
        )
        style.map("Light.TCheckbutton", background=[("active", BG_APP)])

        style.configure(
            "Panel.TCheckbutton",
            background=BG_APP,
            foreground=TXT_MUTED,
            font=self.font_subtitle,
        )
        style.map(
            "Panel.TCheckbutton",
            background=[("active", BG_APP)],
            foreground=[("disabled", TXT_STALE)],
        )

        style.configure(
            "Light.Treeview",
            background=BG_PANEL,
            fieldbackground=BG_PANEL,
            foreground=TXT_PRIMARY,
            borderwidth=0,
            rowheight=34,
            font=self.font_body,
        )
        style.configure(
            "Light.Treeview.Heading",
            background=BG_PANEL,
            foreground=TXT_MUTED,
            font=("Helvetica", 11, "bold"),
            borderwidth=1,
            bordercolor=BORDER_LIGHT,
            relief="flat",
        )
        style.map(
            "Light.Treeview",
            background=[("selected", "#DBEAFE")], 
            foreground=[("selected", ACCENT), ("disabled", TXT_STALE)],
        )
        style.layout("Light.Treeview", [("Light.Treeview.treearea", {"sticky": "nswe"})])

    def _build_layout(self) -> None:
        root = tk.Frame(self, bg=BG_APP, padx=30, pady=24)
        root.pack(fill="both", expand=True)
        root.rowconfigure(2, weight=1)
        root.columnconfigure(0, weight=1)

        self._build_header(root)
        self._build_status_strip(root)
        self._build_body(root)
        self._build_footer(root)

    def _build_header(self, parent: tk.Frame) -> None:
        header = tk.Frame(parent, bg=BG_APP)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 24))
        header.columnconfigure(1, weight=1)

        title_box = tk.Frame(header, bg=BG_APP)
        title_box.grid(row=0, column=0, sticky="w")
        tk.Label(title_box, text="Plataforma de Telemetría", font=self.font_title, bg=BG_APP, fg=TXT_PRIMARY).pack(anchor="w")
        tk.Label(
            title_box, text="Cliente Operador TCP", font=self.font_subtitle, bg=BG_APP, fg=TXT_MUTED
        ).pack(anchor="w")

        conn_box = tk.Frame(header, bg=BG_APP)
        conn_box.grid(row=0, column=1, sticky="e")

        tk.Label(conn_box, text="Host", bg=BG_APP, fg=TXT_MUTED).grid(row=0, column=0, padx=(0, 8))
        self.entry_host = ttk.Entry(conn_box, width=12, style="Light.TEntry")
        self.entry_host.insert(0, DEFAULT_HOST)
        self.entry_host.grid(row=0, column=1, padx=(0, 16))

        tk.Label(conn_box, text="Puerto", bg=BG_APP, fg=TXT_MUTED).grid(row=0, column=2, padx=(0, 8))
        self.entry_port = ttk.Entry(conn_box, width=7, style="Light.TEntry")
        self.entry_port.insert(0, str(DEFAULT_PORT))
        self.entry_port.grid(row=0, column=3, padx=(0, 24))

        self.badge_conexion = tk.Canvas(conn_box, width=12, height=12, bg=BG_APP, highlightthickness=0)
        self._dot = self.badge_conexion.create_oval(2, 2, 10, 10, fill=TXT_FAINT, outline="")
        self.badge_conexion.grid(row=0, column=4, padx=(0, 6))
        self.lbl_conexion = tk.Label(conn_box, text="Desconectado", bg=BG_APP, fg=TXT_MUTED)
        self.lbl_conexion.grid(row=0, column=5, padx=(0, 24))

        self.chk_auto_refresh = ttk.Checkbutton(
            conn_box,
            text="Refresco automático",
            variable=self._auto_refresh,
            style="Panel.TCheckbutton",
            command=self._toggle_auto_refresh,
        )
        self.chk_auto_refresh.grid(row=0, column=6, padx=(0, 16))

        self.btn_refrescar = ttk.Button(conn_box, text="＋  Actualizar", style="Accent.TButton", command=self.refrescar_todo)
        self.btn_refrescar.grid(row=0, column=7)

        self.var_aviso_conexion = tk.StringVar(value="")
        self.lbl_aviso_conexion = tk.Label(
            conn_box,
            textvariable=self.var_aviso_conexion,
            bg=BG_APP,
            fg=WARNING,
            font=("Helvetica", 9),
        )
        self.lbl_aviso_conexion.grid(row=1, column=4, columnspan=4, sticky="e", pady=(6, 0))

    def _build_status_strip(self, parent: tk.Frame) -> None:
        strip = tk.Frame(parent, bg=BG_APP)
        strip.grid(row=1, column=0, sticky="ew", pady=(0, 24))
        for i in range(5):
            strip.columnconfigure(i, weight=1)

        self._stat_vars: dict[str, tk.StringVar] = {}
        self._stat_value_labels: list[tk.Label] = []
        self._stat_text_labels: list[tk.Label] = []
        stats = [
            ("registered_nodes", "Total Registrados", TOP_CARD_COLORS["BLUE"]),
            ("active_nodes", "Nodos Activos", TOP_CARD_COLORS["GREEN"]),
            ("alert_count", "Alertas Globales", TOP_CARD_COLORS["RED"]),
            ("udp_received", "Paquetes Recibidos", TOP_CARD_COLORS["PURPLE"]),
            ("udp_lost", "Paquetes Perdidos", TOP_CARD_COLORS["ORANGE"]),
        ]
        for col, (key, label, color) in enumerate(stats):
            # Estilo simulado Neumórfico
            card = tk.Frame(
                strip,
                bg=BG_CARD,
                highlightbackground=BORDER_LIGHT,
                highlightcolor=BORDER_DARK,
                highlightthickness=1,
                relief="flat",
            )
            card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 16, 0))

            bar = tk.Frame(card, bg=color, width=8)
            bar.pack(side="left", fill="y")

            inner = tk.Frame(card, bg=BG_CARD, padx=20, pady=16)
            inner.pack(side="left", fill="both", expand=True)

            var = tk.StringVar(value="—")
            self._stat_vars[key] = var
            value_label = tk.Label(inner, textvariable=var, font=self.font_stat_value, bg=BG_CARD, fg=TXT_PRIMARY)
            value_label.pack(anchor="w")
            text_label = tk.Label(inner, text=label, font=self.font_subtitle, bg=BG_CARD, fg=TXT_MUTED)
            text_label.pack(anchor="w")
            self._stat_value_labels.append(value_label)
            self._stat_text_labels.append(text_label)

    def _build_body(self, parent: tk.Frame) -> None:
        body = tk.Frame(parent, bg=BG_APP)
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=0, minsize=340)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_nodes_panel(body)
        self._build_detail_and_alerts(body)

    def _build_nodes_panel(self, parent: tk.Frame) -> None:
        panel = tk.Frame(parent, bg=BG_PANEL, highlightbackground=BORDER_LIGHT, highlightthickness=1)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
        panel.rowconfigure(2, weight=1)
        panel.columnconfigure(0, weight=1)

        header = tk.Frame(panel, bg=BG_PANEL)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 12))
        tk.Label(header, text="Directorio de Nodos", font=self.font_section, bg=BG_PANEL, fg=TXT_PRIMARY).pack(anchor="w")

        search_box = tk.Frame(panel, bg=BG_PANEL)
        search_box.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 16))
        search_box.columnconfigure(0, weight=1)

        self.var_busqueda = tk.StringVar()
        self.var_busqueda.trace_add("write", lambda *_: self._filtrar_nodos())
        self.entry_busqueda = ttk.Entry(search_box, textvariable=self.var_busqueda, style="Light.TEntry")
        self.entry_busqueda.grid(row=0, column=0, sticky="ew")
        self.entry_busqueda.insert(0, "")
        self._set_placeholder(self.entry_busqueda, "Buscar identificador...")

        tree_frame = tk.Frame(panel, bg=BG_PANEL)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree_nodos = ttk.Treeview(tree_frame, columns=("estado",), show="tree headings", style="Light.Treeview", selectmode="browse")
        self.tree_nodos.heading("#0", text="Nodo ID")
        self.tree_nodos.heading("estado", text="Estado")
        self.tree_nodos.column("#0", width=170, anchor="w")
        self.tree_nodos.column("estado", width=100, anchor="center")
        self.tree_nodos.tag_configure("activo", foreground=SUCCESS)
        self.tree_nodos.tag_configure("inactivo", foreground=TXT_FAINT)
        self.tree_nodos.grid(row=0, column=0, sticky="nsew")
        self.tree_nodos.bind("<<TreeviewSelect>>", self._on_seleccionar_nodo)

    def _build_detail_and_alerts(self, parent: tk.Frame) -> None:
        right = tk.Frame(parent, bg=BG_APP)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_detail_card(right)
        self._build_alerts_panel(right)

    def _build_detail_card(self, parent: tk.Frame) -> None:
        card = tk.Frame(parent, bg=BG_PANEL, highlightbackground=BORDER_LIGHT, highlightthickness=1)
        card.grid(row=0, column=0, sticky="ew", pady=(0, 24))
        card.columnconfigure(0, weight=1)

        top = tk.Frame(card, bg=BG_PANEL)
        top.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 8))
        top.columnconfigure(0, weight=1)

        self.var_nodo_titulo = tk.StringVar(value="Selecciona un nodo")
        tk.Label(top, textvariable=self.var_nodo_titulo, font=self.font_section, bg=BG_PANEL, fg=TXT_PRIMARY).grid(row=0, column=0, sticky="w")

        self.badge_estado_nodo = tk.Label(top, text="—", font=("Helvetica", 11, "bold"), bg=BG_PANEL, fg=TXT_MUTED, padx=14, pady=6)
        self.badge_estado_nodo.grid(row=0, column=1, sticky="e")

        self.var_ultima_medicion = tk.StringVar(value="")
        tk.Label(card, textvariable=self.var_ultima_medicion, font=self.font_subtitle, bg=BG_PANEL, fg=TXT_MUTED).grid(row=1, column=0, sticky="w", padx=30, pady=(0, 20))

        metrics = tk.Frame(card, bg=BG_PANEL)
        metrics.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 30))
        for i in range(4):
            metrics.columnconfigure(i, weight=1)

        self._metric_widgets: dict[str, dict[str, object]] = {}
        for col, key in enumerate(("TEMP", "HUM", "ENERGY", "VIBRATION")):
            label_text, unit = METRIC_LABELS[key]
            color = METRIC_COLORS[key]

            tile = tk.Frame(metrics, bg=BG_PANEL, highlightbackground=BORDER_LIGHT, highlightthickness=1)
            tile.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 16, 0))

            bar = tk.Frame(tile, bg=color, height=6) 
            bar.pack(side="top", fill="x")

            inner = tk.Frame(tile, bg=BG_PANEL, padx=20, pady=20)
            inner.pack(side="top", fill="both", expand=True)

            val_var = tk.StringVar(value="—")
            value_label = tk.Label(inner, textvariable=val_var, font=self.font_metric_value, bg=BG_PANEL, fg=TXT_PRIMARY)
            value_label.pack(anchor="w")
            text_label = tk.Label(inner, text=f"{label_text} ({unit})", font=self.font_metric_label, bg=BG_PANEL, fg=TXT_MUTED)
            text_label.pack(anchor="w")

            self._metric_widgets[key] = {
                "var": val_var,
                "value_label": value_label,
                "text_label": text_label,
            }

    def _build_alerts_panel(self, parent: tk.Frame) -> None:
        panel = tk.Frame(parent, bg=BG_PANEL, highlightbackground=BORDER_LIGHT, highlightthickness=1)
        panel.grid(row=1, column=0, sticky="nsew")
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)

        header = tk.Frame(panel, bg=BG_PANEL)
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 16))
        tk.Label(
            header,
            text="Registro Global de Alertas",
            font=self.font_section,
            bg=BG_PANEL,
            fg=TXT_PRIMARY,
        ).pack(side="left")

        filter_box = tk.Frame(header, bg=BG_PANEL)
        filter_box.pack(side="right")

        tk.Label(
            filter_box,
            text="Mostrar:",
            font=self.font_body,
            bg=BG_PANEL,
            fg=TXT_MUTED,
        ).pack(side="left", padx=(0, 8))

        self.var_filtro_alertas = tk.StringVar(value="Todos los nodos")
        self.combo_filtro_alertas = ttk.Combobox(
            filter_box,
            textvariable=self.var_filtro_alertas,
            values=("Todos los nodos",),
            state="readonly",
            width=18,
        )
        self.combo_filtro_alertas.pack(side="left")
        self.combo_filtro_alertas.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._aplicar_filtro_alertas(),
        )

        tree_frame = tk.Frame(panel, bg=BG_PANEL)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 30))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        columns = ("nodo", "tipo", "valor", "hora")
        self.tree_alertas = ttk.Treeview(tree_frame, columns=columns, show="headings", style="Light.Treeview")
        headings = {
            "nodo": ("Identificador", 120),
            "tipo": ("Tipo de Evento", 220),
            "valor": ("Valor Registrado", 140),
            "hora": ("Marca de Tiempo", 200),
        }
        for col, (text, width) in headings.items():
            self.tree_alertas.heading(col, text=text)
            self.tree_alertas.column(col, width=width, anchor="center")

        self.tree_alertas.tag_configure("critica", foreground=DANGER)
        self.tree_alertas.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_alertas.yview)
        self.tree_alertas.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")

    def _build_footer(self, parent: tk.Frame) -> None:
        footer = tk.Frame(parent, bg=BG_APP)
        footer.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        self.var_footer = tk.StringVar(value="Sistema iniciado. Esperando conexión...")
        tk.Label(footer, textvariable=self.var_footer, font=self.font_subtitle, bg=BG_APP, fg=TXT_MUTED).pack(side="left")

    def _set_placeholder(self, entry: ttk.Entry, text: str) -> None:
        entry.insert(0, text)
        entry.configure(foreground=TXT_FAINT)
        def on_focus_in(_event: object) -> None:
            if entry.get() == text:
                entry.delete(0, "end")
                entry.configure(foreground=TXT_PRIMARY)
        def on_focus_out(_event: object) -> None:
            if not entry.get():
                entry.insert(0, text)
                entry.configure(foreground=TXT_FAINT)
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def _actualizar_conexion(self, ok: bool, mensaje: str = "") -> None:
        self._connected = ok
        if ok:
            self._last_success_time = time.strftime("%H:%M:%S")
            self.badge_conexion.itemconfig(self._dot, fill=SUCCESS)
            self.lbl_conexion.configure(text="Conectado", fg=SUCCESS)
            self.var_aviso_conexion.set("")
            self._set_data_controls_enabled(True)
            self._set_stale_appearance(False)
            return

        self.badge_conexion.itemconfig(self._dot, fill=DANGER)
        self.lbl_conexion.configure(text="Desconectado", fg=DANGER)
        if self._last_success_time:
            self.var_aviso_conexion.set(
                f"Mostrando los últimos datos recibidos · "
                f"Última actualización exitosa: {self._last_success_time}"
            )
        else:
            self.var_aviso_conexion.set("Sin datos del servidor. Presiona Actualizar para reintentar.")
        self._set_data_controls_enabled(False)
        self._set_stale_appearance(True)

    def _set_data_controls_enabled(self, enabled: bool) -> None:
        """Habilita solo los controles que dependen de datos del servidor."""
        if enabled:
            self.entry_busqueda.state(["!disabled"])
            self.tree_nodos.state(["!disabled"])
            self.chk_auto_refresh.state(["!disabled"])
            self.combo_filtro_alertas.configure(state="readonly")
            return

        self._auto_refresh.set(False)
        self.entry_busqueda.state(["disabled"])
        self.tree_nodos.selection_remove(self.tree_nodos.selection())
        self.tree_nodos.state(["disabled"])
        self.chk_auto_refresh.state(["disabled"])
        self.combo_filtro_alertas.configure(state="disabled")

    def _set_stale_appearance(self, stale: bool) -> None:
        """Pone en gris los datos anteriores sin borrarlos ni falsearlos."""
        value_color = TXT_STALE if stale else TXT_PRIMARY
        text_color = TXT_STALE if stale else TXT_MUTED

        for label in self._stat_value_labels:
            label.configure(fg=value_color)
        for label in self._stat_text_labels:
            label.configure(fg=text_color)
        for widgets in self._metric_widgets.values():
            widgets["value_label"].configure(fg=value_color)
            widgets["text_label"].configure(fg=text_color)

        if stale:
            self.tree_nodos.tag_configure("activo", foreground=TXT_STALE)
            self.tree_nodos.tag_configure("inactivo", foreground=TXT_STALE)
            self.tree_alertas.tag_configure("critica", foreground=TXT_STALE)
            self.badge_estado_nodo.configure(bg=TXT_STALE, fg="#FFFFFF")
        else:
            self.tree_nodos.tag_configure("activo", foreground=SUCCESS)
            self.tree_nodos.tag_configure("inactivo", foreground=TXT_FAINT)
            self.tree_alertas.tag_configure("critica", foreground=DANGER)

    def _set_footer(self, texto: str) -> None:
        marca = time.strftime("%H:%M:%S")
        self.var_footer.set(f"[{marca}] {texto}")

    def _lanzar_tarea(self, nombre: str, funcion, *args) -> None:
        def trabajo() -> None:
            try:
                resultado = funcion(*args)
                self._task_queue.put((nombre, resultado))
            except (ClienteError, ProtocolError) as exc:
                self._task_queue.put((f"{nombre}_error", str(exc)))
            except Exception as exc: 
                self._task_queue.put((f"{nombre}_error", f"Error inesperado: {exc}"))
        threading.Thread(target=trabajo, daemon=True).start()

    def _procesar_cola(self) -> None:
        try:
            while True:
                nombre, dato = self._task_queue.get_nowait()
                self._despachar_resultado(nombre, dato)
        except queue.Empty:
            pass
        finally:
            self.after(150, self._procesar_cola)

    def _despachar_resultado(self, nombre: str, dato: object) -> None:
        if nombre == "status" and isinstance(dato, SystemStatus):
            self._actualizar_conexion(True)
            self._mostrar_estado(dato)
        elif nombre == "nodos" and isinstance(dato, list):
            self._actualizar_conexion(True)
            self._mostrar_nodos(dato)
        elif nombre == "nodo" and isinstance(dato, NodeData):
            self._actualizar_conexion(True)
            self._mostrar_detalle_nodo(dato)
        elif nombre == "alertas" and isinstance(dato, list):
            self._actualizar_conexion(True)
            self._mostrar_alertas(dato)
        elif nombre.endswith("_error"):
            self._actualizar_conexion(False)
            self._set_footer(str(dato))

    def _leer_conexion_formulario(self) -> None:
        host = self.entry_host.get().strip() or DEFAULT_HOST
        try:
            port = int(self.entry_port.get().strip() or DEFAULT_PORT)
        except ValueError:
            port = DEFAULT_PORT
        self.cliente.configurar(host, port)

    def refrescar_todo(self) -> None:
        self._leer_conexion_formulario()
        self._set_footer("Sincronizando con el servidor central...")
        self._lanzar_tarea("status", self.cliente.obtener_estado_sistema)
        self._lanzar_tarea("nodos", self.cliente.obtener_nodos)
        self._lanzar_tarea("alertas", self.cliente.obtener_alertas)
        if self._selected_node_id:
            self._lanzar_tarea("nodo", self.cliente.obtener_nodo, self._selected_node_id)

    def _toggle_auto_refresh(self) -> None:
        if self._auto_refresh.get():
            self._ciclo_auto_refresh()

    def _ciclo_auto_refresh(self) -> None:
        if not self._auto_refresh.get():
            return
        self.refrescar_todo()
        self.after(AUTO_REFRESH_MS, self._ciclo_auto_refresh)

    def _filtrar_nodos(self) -> None:
        if not hasattr(self, "tree_nodos"):
            return 
        filtro = self.var_busqueda.get().strip().upper()
        if filtro.startswith("BUSCAR"): 
            filtro = ""
        self._mostrar_nodos(self._nodes_cache, filtro)

    def _on_seleccionar_nodo(self, _event: object) -> None:
        seleccion = self.tree_nodos.selection()
        if not seleccion:
            return
        node_id = seleccion[0]
        self._selected_node_id = node_id
        self._leer_conexion_formulario()
        self._set_footer(f"Consultando métricas de {node_id}...")
        self._lanzar_tarea("nodo", self.cliente.obtener_nodo, node_id)

    def _mostrar_estado(self, status: SystemStatus) -> None:
        self._stat_vars["registered_nodes"].set(str(status.registered_nodes))
        self._stat_vars["active_nodes"].set(str(status.active_nodes))
        self._stat_vars["alert_count"].set(str(status.alert_count))
        self._stat_vars["udp_received"].set(str(status.udp_received))
        self._stat_vars["udp_lost"].set(str(status.udp_lost))
        self._set_footer("Estado del sistema actualizado.")

    def _mostrar_nodos(self, nodos: list[NodeSummary], filtro: str = "") -> None:
        self._nodes_cache = nodos

        opciones_alertas = ["Todos los nodos"]
        opciones_alertas.extend(
            nodo.node_id
            for nodo in sorted(nodos, key=lambda elemento: elemento.node_id)
        )
        self.combo_filtro_alertas.configure(values=opciones_alertas)

        if self.var_filtro_alertas.get() not in opciones_alertas:
            self.var_filtro_alertas.set("Todos los nodos")
            self._aplicar_filtro_alertas()

        seleccionado_previo = self._selected_node_id
        for item in self.tree_nodos.get_children():
            self.tree_nodos.delete(item)
        for nodo in sorted(nodos, key=lambda n: n.node_id):
            if filtro and filtro not in nodo.node_id.upper():
                continue
            tag = "activo" if nodo.is_active else "inactivo"
            icono = "●" if nodo.is_active else "○"
            estado_visible = "ACTIVO" if nodo.is_active else "INACTIVO"
            self.tree_nodos.insert(
                "",
                "end",
                iid=nodo.node_id,
                text=f"{icono}   {nodo.node_id}",
                values=(estado_visible,),
                tags=(tag,),
            )
        if seleccionado_previo and self.tree_nodos.exists(seleccionado_previo):
            self.tree_nodos.selection_set(seleccionado_previo)
        self._set_footer(f"Sincronización completada: {len(nodos)} nodos detectados.")

    def _mostrar_detalle_nodo(self, nodo: NodeData) -> None:
        self.var_nodo_titulo.set(f"{nodo.node_id}")
        if nodo.is_active:
            self.badge_estado_nodo.configure(text="OPERATIVO", bg=SUCCESS, fg="#FFFFFF")
        else:
            self.badge_estado_nodo.configure(text="FUERA DE LÍNEA", bg=TXT_FAINT, fg="#FFFFFF")
        self.var_ultima_medicion.set(f"Última transmisión registrada: {nodo.last_seen}")
        valores = {"TEMP": nodo.temperature, "HUM": nodo.humidity, "ENERGY": nodo.energy, "VIBRATION": nodo.vibration}
        for key, valor in valores.items():
            var = self._metric_widgets[key]["var"]
            var.set(f"{valor:.1f}" if valor is not None else "—")
        self._set_footer(f"Métricas de {nodo.node_id} actualizadas.")

    def _mostrar_alertas(self, alertas: list[Alert]) -> None:
        self._alerts_cache = alertas
        self._aplicar_filtro_alertas()

    def _aplicar_filtro_alertas(self) -> None:
        nodo_seleccionado = self.var_filtro_alertas.get()

        for item in self.tree_alertas.get_children():
            self.tree_alertas.delete(item)

        alertas_filtradas = self._alerts_cache
        if nodo_seleccionado != "Todos los nodos":
            alertas_filtradas = [
                alerta
                for alerta in self._alerts_cache
                if alerta.node_id == nodo_seleccionado
            ]

        alertas_ordenadas = sorted(
            alertas_filtradas,
            key=lambda alerta: alerta.timestamp,
            reverse=True,
        )

        for alerta in alertas_ordenadas:
            etiqueta = ALERT_LABELS.get(alerta.alert_type, alerta.alert_type)
            self.tree_alertas.insert(
                "",
                "end",
                values=(
                    alerta.node_id,
                    etiqueta,
                    f"{alerta.value:.1f}",
                    alerta.timestamp,
                ),
                tags=("critica",),
            )

        cantidad = len(alertas_ordenadas)
        if nodo_seleccionado == "Todos los nodos":
            self._set_footer(
                f"Mostrando {cantidad} alertas de todos los nodos."
            )
        else:
            self._set_footer(
                f"Mostrando {cantidad} alertas de {nodo_seleccionado}."
            )

def run() -> None:
    app = OperatorApp()
    app.mainloop()

if __name__ == "__main__":
    run()
