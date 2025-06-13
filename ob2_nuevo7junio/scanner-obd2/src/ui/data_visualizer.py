"""
data_visualizer.py - Interfaz gráfica simple para visualizar datos OBD-II en tiempo real
"""
import sys
import os
import importlib.util
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QLineEdit, QGroupBox, QCheckBox, QTabWidget, QHBoxLayout, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem)
from PySide6.QtCore import QTimer, Qt, Signal, QObject
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from ui.widgets.simple_gauge import SpeedometerGaugeWidget
from ui.tuning_widget import TuningWidget
from ui.pid_acquisition import PIDAcquisitionTab
import pyqtgraph as pg  # <--- NUEVO para gráficos en tiempo real

# Cargar pids_ext.py directamente desde la ruta absoluta
pids_path = '/Users/ignacioeltit/git/proyecto01junio/src/obd/pids_ext.py'
spec = importlib.util.spec_from_file_location('pids_ext', pids_path)
if spec and spec.loader:
    pids_ext = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pids_ext)
    PIDS = pids_ext.PIDS
    normalizar_pid = pids_ext.normalizar_pid
else:
    raise ImportError('No se pudo cargar pids_ext.py')

GAUGE_COLORS = [
    '#00bcd4', '#ff9800', '#e91e63', '#4caf50', '#ffeb3b', '#9c27b0', '#f44336', '#3f51b5', '#8bc34a', '#607d8b'
]
def get_gauge_color(idx):
    from PySide6.QtGui import QColor
    return QColor(GAUGE_COLORS[idx % len(GAUGE_COLORS)])

class CanSignalViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Señal", "Valor", "Unidad"])
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Señales CAN Simuladas</b>"))
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.signal_names = []
    def update_can_data(self, data_dict):
        self.table.setRowCount(len(data_dict))
        for i, (sig, info) in enumerate(data_dict.items()):
            self.table.setItem(i, 0, QTableWidgetItem(str(sig)))
            self.table.setItem(i, 1, QTableWidgetItem(str(info['value'])))
            self.table.setItem(i, 2, QTableWidgetItem(str(info.get('unit', ''))))

class AsyncBackendBridge(QObject):
    vin_updated = Signal(str)
    connection_status = Signal(bool)
    pid_status = Signal(str, bool)
    log_event = Signal(str)
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
    def start(self):
        import asyncio
        asyncio.create_task(self.backend.run(self))
    def on_vin(self, vin):
        self.vin_updated.emit(vin)
    def on_connection(self, ok):
        self.connection_status.emit(ok)
    def on_pid_status(self, pid, is_alive):
        self.pid_status.emit(pid, is_alive)
    def on_log(self, msg):
        self.log_event.emit(msg)

class GaugeBridge(QObject):
    speedChanged = Signal(float)
    rpmChanged = Signal(float)
    def __init__(self):
        super().__init__()
    def set_speed(self, value):
        self.speedChanged.emit(value)
    def set_rpm(self, value):
        self.rpmChanged.emit(value)

class DataVisualizer(QWidget):
    def __init__(self, get_data_fn, pid_manager=None, elm327=None, parse_pid_response=None, backend=None):
        super().__init__()
        self.get_data_fn = get_data_fn
        self.pid_manager = pid_manager
        self.elm327 = elm327
        self.parse_pid_response = parse_pid_response
        self.backend = backend
        self.labels = {}
        self.checkboxes = {}
        self.selected_pids = set()
        self.filter_text = ""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(500)
        self.vehicle_id_mode = 0
        self.vehicle_info = {}
        self.gauge_widgets = {}
        # --- MODO DEMO ---
        self.demo_mode = False
        self.demo_timer = QTimer()
        self.demo_timer.timeout.connect(self._update_demo_gauges)
        self._demo_angle = 0
        self.graph_curves = {}  # <--- NUEVO: para manejar las curvas de los PIDs
        self.graph_data = {}    # <--- NUEVO: historial de datos para cada PID
        self.graph_timer = QTimer()
        self.graph_timer.timeout.connect(self.update_graphs)
        self.init_ui()  # <-- Primero inicializa la UI (crea self.tabs)
        self.tuning_widget = TuningWidget(vehicle_info=self.vehicle_info)
        self.tabs.addTab(self.tuning_widget, "Tuning")

        # Nuevo código para GaugeBridge y QWebChannel
        self.gauge_bridge = GaugeBridge()
        self.gauge_channel = QWebChannel()
        self.gauge_channel.registerObject('gauge_bridge', self.gauge_bridge)
        self.gauge_webview.page().setWebChannel(self.gauge_channel)

    def set_demo_mode(self, enabled: bool):
        self.demo_mode = enabled
        if enabled:
            self.demo_timer.start(60)
        else:
            self.demo_timer.stop()

    def _update_demo_gauges(self):
        # Simula valores animados tipo racing
        import math, random
        self._demo_angle += 0.04
        for name, gauge in self.gauge_widgets.items():
            # Oscilación tipo racing
            if "RPM" in name.upper():
                v = 3000 + 2500 * math.sin(self._demo_angle)
            elif "VEL" in name.upper() or "SPEED" in name.upper():
                v = 80 + 60 * math.sin(self._demo_angle + 1)
            elif "TEMP" in name.upper():
                v = 90 + 10 * math.sin(self._demo_angle + 2)
            elif "ACEITE" in name.upper() or "OIL" in name.upper():
                v = 40 + 20 * math.sin(self._demo_angle + 3)
            else:
                v = random.uniform(gauge.min_value, gauge.max_value)
            gauge.set_value(v)

    def init_ui(self):
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from main import get_makes_and_models
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.setMinimumSize(900, 600)
        self.setWindowTitle("Scanner OBD2 Premium")
        # Inicializar catálogo de marcas/modelos
        self._vehicle_catalog = get_makes_and_models()
        # Barra de estado
        self.label_status = QLabel("Estado: Desconectado")
        self.label_status.setStyleSheet("font-weight: bold; color: red; margin-bottom: 8px;")
        main_layout.addWidget(self.label_status)
        # Botones principales
        btns_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar ELM327")
        self.btn_read_vin = QPushButton("Leer VIN")
        self.btn_scan_protocols = QPushButton("Escanear Protocolos")
        btns_layout.addWidget(self.btn_connect)
        btns_layout.addWidget(self.btn_read_vin)
        btns_layout.addWidget(self.btn_scan_protocols)
        main_layout.addLayout(btns_layout)
        # Campos VIN y Protocolo
        self.le_vin = QLineEdit()
        self.le_vin.setReadOnly(True)
        main_layout.addWidget(QLabel("VIN:"))
        main_layout.addWidget(self.le_vin)
        self.le_protocol = QLineEdit()
        self.le_protocol.setReadOnly(True)
        main_layout.addWidget(QLabel("Protocolo:"))
        main_layout.addWidget(self.le_protocol)
        # Widgets para selección y visualización de PID
        self.btn_scan_pids = QPushButton("Buscar PIDs")
        self.btn_start_live = QPushButton("Iniciar lectura")
        self.pid_selector = QComboBox()
        self.label_pid_value = QLabel("Esperando datos...")
        main_layout.addWidget(self.btn_scan_pids)
        main_layout.addWidget(QLabel("Seleccionar PID:"))
        main_layout.addWidget(self.pid_selector)
        main_layout.addWidget(self.btn_start_live)
        main_layout.addWidget(self.label_pid_value)
        # --- NUEVA PESTAÑA MULTIPID ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        # Tab 1: Actual (PID único)
        tab_uno = QWidget()
        tab_uno_layout = QVBoxLayout(tab_uno)
        tab_uno_layout.addWidget(QLabel("Lectura de PID único (flujo clásico)"))
        tab_uno_layout.addWidget(self.btn_scan_pids)
        tab_uno_layout.addWidget(self.pid_selector)
        tab_uno_layout.addWidget(self.btn_start_live)
        tab_uno_layout.addWidget(self.label_pid_value)
        self.tabs.addTab(tab_uno, "PID único")
        # Tab 2: MultiPID
        self.tab_pids = QWidget()
        layout_pids = QVBoxLayout(self.tab_pids)
        # --- Buscador para multipids ---
        self.pid_search = QLineEdit()
        self.pid_search.setPlaceholderText("Buscar PID...")
        layout_pids.addWidget(self.pid_search)
        self.pid_list = QListWidget()
        self.pid_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout_pids.addWidget(QLabel("Selecciona PIDs a monitorear:"))
        layout_pids.addWidget(self.pid_list)
        self.btn_start_stream = QPushButton("Iniciar Stream")
        layout_pids.addWidget(self.btn_start_stream)
        self.values_layout = QVBoxLayout()
        layout_pids.addLayout(self.values_layout)
        self.tabs.addTab(self.tab_pids, "PIDs múltiples")
        # Tab 3: Gauges (ahora usando QWebEngineView con canvas-gauges)
        self.tab_gauges = QWidget()
        self.gauges_layout = QVBoxLayout()
        self.tab_gauges.setLayout(self.gauges_layout)
        self.gauges_layout.addWidget(QLabel("<b>Visualización de Gauges</b>"))
        self.gauge_webview = QWebEngineView()
        html_path = os.path.join(os.path.dirname(__file__), "canvas_gauge.html")
        self.gauge_webview.load(f"file://{html_path}")
        self.gauges_layout.addWidget(self.gauge_webview)
        self.tabs.addTab(self.tab_gauges, "Gauges")
        # --- NUEVA PESTAÑA DE GRÁFICOS ---
        self.tab_graphs = QWidget()
        self.graphs_layout = QVBoxLayout(self.tab_graphs)
        self.tab_graphs.setLayout(self.graphs_layout)
        self.graphs_layout.addWidget(QLabel("<b>Gráficos en Tiempo Real</b>"))
        # Selector de PIDs a graficar
        self.graph_pid_selector = QListWidget()
        self.graph_pid_selector.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.graphs_layout.addWidget(QLabel("Selecciona PIDs a graficar:"))
        self.graphs_layout.addWidget(self.graph_pid_selector)
        # Widget de gráfico
        self.graph_plot = pg.PlotWidget(title="Datos OBD2 en Tiempo Real")
        self.graph_plot.showGrid(x=True, y=True)
        self.graphs_layout.addWidget(self.graph_plot)  # PyQtGraph PlotWidget ya es un QWidget compatible
        self.tabs.addTab(self.tab_graphs, "Gráficos")
        # Botón para activar modo demo visual
        self.btn_demo = QPushButton("Modo Demo Visual")
        self.btn_demo.setCheckable(True)
        self.btn_demo.setStyleSheet("background: #444; color: #fff; font-weight: bold;")
        self.btn_demo.toggled.connect(self.set_demo_mode)
        btns_layout.addWidget(self.btn_demo)
        # --- Fallback manual de vehículo ---
        self.label_fallback = QLabel("<b>Selecciona Marca, Modelo y Año manualmente si el VIN no es válido</b>")
        self.label_fallback.setStyleSheet("color: #ff9800; font-size: 14px; margin-top: 10px;")
        self.label_fallback.setVisible(False)
        self.cb_make = QComboBox()
        self.cb_make.setEditable(True)
        self.cb_make.setVisible(False)
        self.cb_model = QComboBox()
        self.cb_model.setEditable(True)
        self.cb_model.setVisible(False)
        self.cb_year = QComboBox()
        self.cb_year.setEditable(True)
        self.cb_year.setVisible(False)
        self.cb_make.currentTextChanged.connect(self.update_model_list)
        self.fallback_layout = QHBoxLayout()
        self.fallback_layout.addWidget(self.cb_make)
        self.fallback_layout.addWidget(self.cb_model)
        self.fallback_layout.addWidget(self.cb_year)
        main_layout.addWidget(self.label_fallback)
        main_layout.addLayout(self.fallback_layout)

        # Pestaña de Adquisición PID Avanzada
        self.pid_acquisition_tab = PIDAcquisitionTab(self)
        self.tabs.addTab(self.pid_acquisition_tab, "Adquisición PID Avanzada")
        # Ahora sí, conectar el filtro del buscador
        self.pid_search.textChanged.connect(self.filtrar_pid_list)

    def set_status(self, msg: str, color: str = "black"):
        self.label_status.setText(msg)
        self.label_status.setStyleSheet(f"font-weight: bold; color: {color}; margin-bottom: 8px;")

    def show_message(self, title, text):
        QMessageBox.information(self, title, text)

    # ...resto de métodos existentes, pero solo los botones públicos arriba...
    def update_data(self):
        # ...existing code...
        # Suponiendo que los valores de los PIDs se obtienen aquí
        # y que self.get_data_fn() devuelve un dict {pid_name: valor}
        if not hasattr(self, 'last_pid_values'):
            self.last_pid_values = {}
        data = self.get_data_fn() if callable(self.get_data_fn) else {}
        if isinstance(data, dict):
            for k, v in data.items():
                self.last_pid_values[k] = v
        # ...existing code...

    def cargar_pids_en_lista(self, commands):
        """Carga los comandos OBD en la lista con checkboxes"""
        from PySide6.QtCore import Qt
        self.pid_list.clear()
        for cmd in commands:
            item = QListWidgetItem(f"{cmd.name} ({cmd.command})")
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.pid_list.addItem(item)
        # También poblar el selector de PIDs para gráficos
        self.graph_pid_selector.clear()
        for cmd in commands:
            item = QListWidgetItem(f"{cmd.name} ({cmd.command})")
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            self.graph_pid_selector.addItem(item)

    def update_graphs(self):
        # Actualiza los gráficos en tiempo real con datos reales
        selected_items = self.graph_pid_selector.selectedItems()
        if not selected_items:
            self.graph_plot.clear()
            self.graph_curves.clear()
            return
        # Asegura que existe el diccionario de últimos valores
        if not hasattr(self, 'last_pid_values'):
            self.last_pid_values = {}
        for item in selected_items:
            cmd = item.data(Qt.ItemDataRole.UserRole)
            pid_name = cmd.name
            if pid_name not in self.graph_data:
                self.graph_data[pid_name] = []
            # Obtener el valor real del PID si está disponible
            value = self.last_pid_values.get(pid_name)
            if value is not None:
                try:
                    v = float(value)
                except Exception:
                    v = 0
                self.graph_data[pid_name].append(v)
            # Limitar historial a 200 puntos
            if len(self.graph_data[pid_name]) > 200:
                self.graph_data[pid_name] = self.graph_data[pid_name][-200:]
        self.graph_plot.clear()
        for item in selected_items:
            cmd = item.data(Qt.ItemDataRole.UserRole)
            pid_name = cmd.name
            if pid_name not in self.graph_curves:
                self.graph_curves[pid_name] = self.graph_plot.plot(pen=pg.mkPen(width=2), name=pid_name)
            ydata = self.graph_data[pid_name]
            xdata = list(range(len(ydata)))
            self.graph_curves[pid_name].setData(xdata, ydata)

    def start_graph_timer(self):
        self.graph_timer.start(200)  # Actualiza cada 200 ms

    def stop_graph_timer(self):
        self.graph_timer.stop()

    def closeEvent(self, a0):
        self.stop_pid_stream()
        self.stop_graph_timer()
        super().closeEvent(a0)

    def setup_tab_signals(self):
        # Detener stream al cambiar de pestaña
        if hasattr(self, 'tabs'):
            self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, idx):
        # Solo detener el stream si salimos de multipid Y de gauges
        if hasattr(self, 'tabs') and hasattr(self, 'tab_pids') and hasattr(self, 'tab_gauges'):
            current_widget = self.tabs.widget(idx)
            if current_widget != self.tab_pids and current_widget != self.tab_gauges:
                self.stop_pid_stream()
        # Iniciar/detener refresco de gráficos al cambiar a la pestaña de gráficos
        if hasattr(self, 'tabs') and hasattr(self, 'tab_graphs'):
            current_widget = self.tabs.widget(idx)
            if current_widget == self.tab_graphs:
                self.start_graph_timer()
            else:
                self.stop_graph_timer()

    def cargar_pids_agrupados_en_lista(self, supported_cmds):
        """Agrupa los comandos OBD por familia y los carga en la lista multipid con checkboxes"""
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtCore import Qt
        import obd
        pid_families = {
            "Motor": [obd.commands['RPM'], obd.commands['ENGINE_LOAD'], obd.commands['COOLANT_TEMP'], obd.commands['INTAKE_TEMP']],
            "Velocidad": [obd.commands['SPEED']],
            "Combustible": [obd.commands['FUEL_LEVEL'], obd.commands['FUEL_PRESSURE'], obd.commands['FUEL_STATUS']],
            "Aire": [obd.commands['INTAKE_PRESSURE'], obd.commands['MAF'], obd.commands['THROTTLE_POS']],
            # Puedes agregar más familias y comandos aquí
        }
        supported = set(supported_cmds)
        self.pid_list.clear()
        for family, cmds in pid_families.items():
            header = QListWidgetItem(f"--- {family} ---")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.pid_list.addItem(header)
            for cmd in cmds:
                if cmd is not None and cmd in supported:
                    item = QListWidgetItem(cmd.name)
                    item.setData(Qt.ItemDataRole.UserRole, cmd)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    self.pid_list.addItem(item)
        self.set_status("PIDs agrupados cargados")

    def enable_vehicle_fallback(self, enabled: bool = True):
        """Habilita o deshabilita la selección manual de vehículo (fallback) y permite ingreso manual si no está en la biblioteca"""
        self.label_fallback.setVisible(enabled)
        self.cb_make.setEnabled(enabled)
        self.cb_make.setVisible(enabled)
        self.cb_model.setEnabled(enabled)
        self.cb_model.setVisible(enabled)
        self.cb_year.setEnabled(enabled)
        self.cb_year.setVisible(enabled)
        if enabled:
            self.cb_make.setEditable(True)
            self.cb_model.setEditable(True)
            self.cb_year.setEditable(True)
            if not hasattr(self, 'btn_save_vehicle'):
                from PySide6.QtWidgets import QPushButton
                self.btn_save_vehicle = QPushButton("Guardar vehículo manualmente")
                self.btn_save_vehicle.clicked.connect(self.save_manual_vehicle)
                main_layout = getattr(self, '_main_layout', None) or self.layout()
                if main_layout:
                    main_layout.addWidget(self.btn_save_vehicle)
            self.btn_save_vehicle.setVisible(True)
        else:
            if hasattr(self, 'btn_save_vehicle'):
                self.btn_save_vehicle.setVisible(False)

    def create_and_connect_save_button(self, parent_layout):
        # Crear botón dentro del layout indicado
        self.btn_save_vehicle = QPushButton("Guardar vehículo manualmente")
        parent_layout.addWidget(self.btn_save_vehicle)
        self.btn_save_vehicle.clicked.connect(self.on_save_manual_vehicle)

    def on_save_manual_vehicle(self):
        make = self.cb_make.currentText()
        model = self.cb_model.currentText()
        year = self.cb_year.currentText()
        data = {"make": make, "model": model, "year": year}

        # Guardar en JSON
        import json, os
        path = os.path.expanduser("~/.scanner_obd2_manual_vehicles.json")
        existing = []
        if os.path.exists(path):
            with open(path, "r") as f:
                existing = json.load(f)
        existing.append(data)
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)

        # Actualizar catálogo y combos
        if not hasattr(self, 'catalog'):
            self.catalog = {}
        self.catalog.setdefault(make, set()).add(model)

        QMessageBox.information(self, "Guardado", f"{make} {model} {year} guardado correctamente")

    # Asegurar que update_model_list existe y está conectado
    def update_model_list(self):
        catalog = getattr(self, '_vehicle_catalog', {})
        if catalog is None:
            catalog = {}
        make = self.cb_make.currentText()
        if make in catalog:
            models = catalog[make]
        else:
            models = []
        self.cb_model.clear()
        self.cb_model.addItems(models)

    def save_manual_vehicle(self):
        """Guarda la marca/modelo/año manualmente ingresados en la biblioteca local"""
        marca = self.cb_make.currentText().strip()
        modelo = self.cb_model.currentText().strip()
        anio = self.cb_year.currentText().strip()
        if not marca or not modelo or not anio:
            QMessageBox.warning(self, "Faltan datos", "Debes ingresar marca, modelo y año.")
            return
        # Cargar catálogo actual
        catalog_path = os.path.join(os.path.dirname(__file__), '../../data/vehicle_makes_models.json')
        if os.path.exists(catalog_path):
            import json
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
        else:
            catalog = {}
        # Agregar o actualizar
        if marca not in catalog:
            catalog[marca] = []
        if modelo not in catalog[marca]:
            catalog[marca].append(modelo)
        # Guardar
        with open(catalog_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "Vehículo guardado", f"{marca} {modelo} ({anio}) guardado en la biblioteca.")

    def leer_vin(self):
        """Lee el VIN del vehículo conectado y lo muestra en la interfaz"""
        import obd
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt
        self.set_status("Leyendo VIN...")
        self.le_vin.setText("")
        self.btn_read_vin.setEnabled(False)
        # Intentar leer VIN usando python-OBD
        def on_vin_read(vin):
            if vin and len(vin) > 10:
                self.set_status(f"VIN leído: {vin}", "green")
                self.le_vin.setText(vin)
                self.enable_vehicle_fallback(False)
                # Detener el temporizador de actualización
                self.timer.stop()
                # Iniciar búsqueda de PIDs automáticamente
                QTimer.singleShot(500, self.buscar_pids)
            else:
                self.set_status("VIN no válido, habilitando selección manual", "red")
                self.le_vin.setText("VIN manual requerido")
                self.enable_vehicle_fallback(True)
                # Ya no se llama a populate_vehicle_fallback()
                # Agregar botón de guardado inmediatamente:
                self.create_and_connect_save_button(self.fallback_layout)

        # Conexión asíncrona para leer VIN
        self.async_vin_reader = obd.Async("socket://192.168.0.10:35000", fast=False, timeout=0.5)
        self.async_vin_reader.add_obd_command(obd.commands['VIN'], callback=on_vin_read)
        self.async_vin_reader.start()

    def buscar_pids(self):
        """Busca los PIDs soportados por el vehículo y los muestra en la interfaz"""
        import obd
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtCore import Qt
        self.set_status("Buscando PIDs soportados...")
        self.pid_selector.clear()
        # Conexión asíncrona para buscar PIDs
        self.async_pid_finder = obd.Async("socket://192.168.0.10:35000", fast=False, timeout=0.5)
        def on_pid_discovery(cmds):
            self.set_status(f"Se encontraron {len(cmds)} PIDs")
            for cmd in cmds:
                item = QListWidgetItem(f"{cmd.name} ({cmd.command})")
                item.setData(Qt.ItemDataRole.UserRole, cmd)
                self.pid_selector.addItem(item)
            # Seleccionar automáticamente algunos PIDs comunes
            for cmd in [obd.commands['RPM'], obd.commands['SPEED'], obd.commands['ENGINE_LOAD']]:
                if cmd in cmds:
                    index = self.pid_selector.findData(cmd, Qt.ItemDataRole.UserRole)
                    if index != -1:
                        self.pid_selector.model().item(index).setCheckState(Qt.CheckState.Checked)
        self.async_pid_finder.add_obd_command(obd.commands['VIN'], callback=on_pid_discovery)
        self.async_pid_finder.start()

    def refresh_gauges_tab(self):
        # Método placeholder, sin lógica de gauges
        pass

    def closeEvent(self, a0):
        self.stop_pid_stream()
        self.stop_graph_timer()
        super().closeEvent(a0)

    def setup_tab_signals(self):
        # Detener stream al cambiar de pestaña
        if hasattr(self, 'tabs'):
            self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, idx):
        current_widget = self.tabs.widget(idx)
        # Detener stream si salimos de multipid Y de gauges (canvas gauges)
        if hasattr(self, 'tab_pids') and hasattr(self, 'tab_gauges'):
            if current_widget != self.tab_pids and current_widget != self.tab_gauges:
                if hasattr(self.backend, 'stop_multipid_stream'): # Asumiendo que el backend tiene este método
                    self.backend.stop_multipid_stream() 
                # self.stop_pid_stream() # Si este método local también es relevante

        # Iniciar/detener refresco de gráficos
        if hasattr(self, 'tab_graphs'):
            if current_widget == self.tab_graphs:
                self.start_graph_timer()
            else:
                self.stop_graph_timer()

    def update_gauge(self, pid_name, value):
        # Actualiza los gauges canvas-gauges vía QWebChannel
        if 'rpm' in pid_name.lower():
            self.gauge_bridge.set_rpm(float(value))
        elif 'vel' in pid_name.lower() or 'speed' in pid_name.lower():
            self.gauge_bridge.set_speed(float(value))
        # ...si hay otros gauges, puedes agregar lógica aquí...

    def filtrar_pid_list(self, text):
        """Filtra la lista de PIDs multipid según el texto de búsqueda"""
        for i in range(self.pid_list.count()):
            item = self.pid_list.item(i)
            visible = text.lower() in item.text().lower()
            item.setHidden(not visible)

    def clear_gauges(self):
        # Método vacío para evitar errores al cerrar la app
        pass