"""
data_visualizer.py - Interfaz gráfica simple para visualizar datos OBD-II en tiempo real
"""
import sys
import os
import importlib.util
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QLineEdit, QGroupBox, QCheckBox, QTabWidget, QHBoxLayout, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem)
from PySide6.QtCore import QTimer, Qt, Signal, QObject
import pyqtgraph as pg  # <--- NUEVO para gráficos en tiempo real
from .pid_acquisition import PIDAcquisitionTab
from .tuning_widget import TuningWidget
from vin_decoder import VinDecoder
from PySide6.QtWidgets import QTextEdit
from .widgets.gauge_realista import RealisticGaugeWidget
from PySide6.QtGui import QColor

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
        self.graph_curves = {}
        self.graph_data = {}
        self.graph_timer = QTimer()
        self.graph_timer.timeout.connect(self.update_graphs)
        self._main_layout = None
        self.init_ui()
        # Eliminar inicialización de TuningWidget si no está implementado o importado
        self.tuning_widget = TuningWidget(vehicle_info=self.vehicle_info)
        self.tabs.addTab(self.tuning_widget, "Tuning")

    def init_ui(self):
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from main import get_makes_and_models
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.setMinimumSize(900, 600)
        self.setWindowTitle("Scanner OBD2 Premium")
        self._vehicle_catalog = get_makes_and_models()
        self.label_status = QLabel("Estado: Desconectado")
        self.label_status.setStyleSheet("font-weight: bold; color: red; margin-bottom: 8px;")
        main_layout.addWidget(self.label_status)
        btns_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar ELM327")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setVisible(True)
        self.btn_read_vin = QPushButton("Leer VIN")
        self.btn_read_vin.setObjectName("btn_read_vin")
        self.btn_scan_protocols = QPushButton("Escanear Protocolos")
        self.btn_scan_protocols.setObjectName("btn_scan_protocols")
        self.btn_scan_pids = QPushButton("Buscar PIDs")
        self.btn_scan_pids.setObjectName("btn_scan_pids")
        self.btn_scan_pids.setVisible(True)
        btns_layout.addWidget(self.btn_connect)
        btns_layout.addWidget(self.btn_read_vin)
        btns_layout.addWidget(self.btn_scan_protocols)
        main_layout.addLayout(btns_layout)
        self.le_vin = QLineEdit()
        self.le_vin.setReadOnly(True)
        main_layout.addWidget(QLabel("VIN:"))
        main_layout.addWidget(self.le_vin)
        self.le_protocol = QLineEdit()
        self.le_protocol.setReadOnly(True)
        main_layout.addWidget(QLabel("Protocolo:"))
        main_layout.addWidget(self.le_protocol)
        self.btn_start_live = QPushButton("Iniciar lectura")
        self.btn_start_live.setObjectName("btn_start_live")
        self.pid_selector = QComboBox()
        self.label_pid_value = QLabel("Esperando datos...")
        main_layout.addWidget(self.btn_scan_pids)
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
        self.btn_start_stream.setObjectName("btn_start_stream")
        layout_pids.addWidget(self.btn_start_stream)
        self.values_layout = QVBoxLayout()
        layout_pids.addLayout(self.values_layout)
        self.tabs.addTab(self.tab_pids, "PIDs múltiples")
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
        # --- NUEVA PESTAÑA DIAGNÓSTICO ---
        self.tab_diagnostico = QWidget()
        diag_layout = QVBoxLayout(self.tab_diagnostico)
        self.btn_read_dtcs = QPushButton("Leer DTCs")
        self.btn_read_dtcs.setObjectName("btn_read_dtcs")
        self.btn_clear_dtcs = QPushButton("Borrar DTCs")
        self.btn_clear_dtcs.setObjectName("btn_clear_dtcs")
        btns_diag = QHBoxLayout()
        btns_diag.addWidget(self.btn_read_dtcs)
        btns_diag.addWidget(self.btn_clear_dtcs)
        diag_layout.addLayout(btns_diag)
        self.dtcs_list_label = QLabel("Estado: No conectado")
        diag_layout.addWidget(self.dtcs_list_label)
        self.dtcs_list = QListWidget()
        diag_layout.addWidget(self.dtcs_list)
        self.tab_diagnostico.setLayout(diag_layout)
        self.tabs.addTab(self.tab_diagnostico, "Diagnóstico")
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
        # self.pid_search.textChanged.connect(self.filtrar_pid_list)  # Corrección: eliminar conexión a método inexistente
        # --- Sección decodificación VIN ---
        vin_section = QGroupBox("Decodificación de VIN")
        vin_layout = QVBoxLayout()
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Ingrese VIN (17 caracteres)")
        self.vin_button = QPushButton("Decodificar VIN")
        self.vin_button.setObjectName("vin_button")
        self.vin_output = QTextEdit()
        self.vin_output.setReadOnly(True)
        vin_layout.addWidget(QLabel("VIN:"))
        vin_layout.addWidget(self.vin_input)
        vin_layout.addWidget(self.vin_button)
        vin_layout.addWidget(self.vin_output)
        vin_section.setLayout(vin_layout)
        main_layout.addWidget(vin_section)
        self.vin_button.clicked.connect(self.decodificar_vin)
        # --- Limpieza de botones sin funcionalidad ---
        self._limpiar_botones_obsoletos()

        # --- Conexión del buscador de PIDs ---
        self.pid_search.textChanged.connect(self._filtrar_pid_list)

        # --- Conexión del botón de stream multipid ---
        self.btn_start_stream.clicked.connect(self._emitir_iniciar_stream)

        # Conexión de botones de diagnóstico al controlador si está disponible
        if hasattr(self, 'controller') and self.controller is not None:
            self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
            self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

    def set_controller(self, controller):
        """Permite asignar el controlador OBDController a la instancia y conectar los botones de diagnóstico."""
        self.controller = controller
        self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
        self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

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
        # Actualizar gauges realistas si existen datos
        rpm = self.last_pid_values.get('RPM')
        speed = self.last_pid_values.get('Velocidad')
        temp = self.last_pid_values.get('Temp Agua')
        if hasattr(self, 'gauge_rpm'):
            if rpm is not None:
                self.gauge_rpm.set_value(rpm)
            if speed is not None:
                self.gauge_speed.set_value(speed)
            if temp is not None:
                self.gauge_temp.set_value(temp)
        # ...existing code...

    def init_ui(self):
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from main import get_makes_and_models
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.setMinimumSize(900, 600)
        self.setWindowTitle("Scanner OBD2 Premium")
        self._vehicle_catalog = get_makes_and_models()
        self.label_status = QLabel("Estado: Desconectado")
        self.label_status.setStyleSheet("font-weight: bold; color: red; margin-bottom: 8px;")
        main_layout.addWidget(self.label_status)
        btns_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar ELM327")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setVisible(True)
        self.btn_read_vin = QPushButton("Leer VIN")
        self.btn_read_vin.setObjectName("btn_read_vin")
        self.btn_scan_protocols = QPushButton("Escanear Protocolos")
        self.btn_scan_protocols.setObjectName("btn_scan_protocols")
        self.btn_scan_pids = QPushButton("Buscar PIDs")
        self.btn_scan_pids.setObjectName("btn_scan_pids")
        self.btn_scan_pids.setVisible(True)
        btns_layout.addWidget(self.btn_connect)
        btns_layout.addWidget(self.btn_read_vin)
        btns_layout.addWidget(self.btn_scan_protocols)
        main_layout.addLayout(btns_layout)
        self.le_vin = QLineEdit()
        self.le_vin.setReadOnly(True)
        main_layout.addWidget(QLabel("VIN:"))
        main_layout.addWidget(self.le_vin)
        self.le_protocol = QLineEdit()
        self.le_protocol.setReadOnly(True)
        main_layout.addWidget(QLabel("Protocolo:"))
        main_layout.addWidget(self.le_protocol)
        self.btn_start_live = QPushButton("Iniciar lectura")
        self.btn_start_live.setObjectName("btn_start_live")
        self.pid_selector = QComboBox()
        self.label_pid_value = QLabel("Esperando datos...")
        main_layout.addWidget(self.btn_scan_pids)
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
        self.btn_start_stream.setObjectName("btn_start_stream")
        layout_pids.addWidget(self.btn_start_stream)
        self.values_layout = QVBoxLayout()
        layout_pids.addLayout(self.values_layout)
        self.tabs.addTab(self.tab_pids, "PIDs múltiples")
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
        # --- NUEVA PESTAÑA DIAGNÓSTICO ---
        self.tab_diagnostico = QWidget()
        diag_layout = QVBoxLayout(self.tab_diagnostico)
        self.btn_read_dtcs = QPushButton("Leer DTCs")
        self.btn_read_dtcs.setObjectName("btn_read_dtcs")
        self.btn_clear_dtcs = QPushButton("Borrar DTCs")
        self.btn_clear_dtcs.setObjectName("btn_clear_dtcs")
        btns_diag = QHBoxLayout()
        btns_diag.addWidget(self.btn_read_dtcs)
        btns_diag.addWidget(self.btn_clear_dtcs)
        diag_layout.addLayout(btns_diag)
        self.dtcs_list_label = QLabel("Estado: No conectado")
        diag_layout.addWidget(self.dtcs_list_label)
        self.dtcs_list = QListWidget()
        diag_layout.addWidget(self.dtcs_list)
        self.tab_diagnostico.setLayout(diag_layout)
        self.tabs.addTab(self.tab_diagnostico, "Diagnóstico")
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
        # self.pid_search.textChanged.connect(self.filtrar_pid_list)  # Corrección: eliminar conexión a método inexistente
        # --- Sección decodificación VIN ---
        vin_section = QGroupBox("Decodificación de VIN")
        vin_layout = QVBoxLayout()
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Ingrese VIN (17 caracteres)")
        self.vin_button = QPushButton("Decodificar VIN")
        self.vin_button.setObjectName("vin_button")
        self.vin_output = QTextEdit()
        self.vin_output.setReadOnly(True)
        vin_layout.addWidget(QLabel("VIN:"))
        vin_layout.addWidget(self.vin_input)
        vin_layout.addWidget(self.vin_button)
        vin_layout.addWidget(self.vin_output)
        vin_section.setLayout(vin_layout)
        main_layout.addWidget(vin_section)
        self.vin_button.clicked.connect(self.decodificar_vin)
        # --- Limpieza de botones sin funcionalidad ---
        self._limpiar_botones_obsoletos()

        # --- Conexión del buscador de PIDs ---
        self.pid_search.textChanged.connect(self._filtrar_pid_list)

        # --- Conexión del botón de stream multipid ---
        self.btn_start_stream.clicked.connect(self._emitir_iniciar_stream)

        # Conexión de botones de diagnóstico al controlador si está disponible
        if hasattr(self, 'controller') and self.controller is not None:
            self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
            self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

    def set_controller(self, controller):
        """Permite asignar el controlador OBDController a la instancia y conectar los botones de diagnóstico."""
        self.controller = controller
        self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
        self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

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
        # Actualizar gauges realistas si existen datos
        rpm = self.last_pid_values.get('RPM')
        speed = self.last_pid_values.get('Velocidad')
        temp = self.last_pid_values.get('Temp Agua')
        if hasattr(self, 'gauge_rpm'):
            if rpm is not None:
                self.gauge_rpm.set_value(rpm)
            if speed is not None:
                self.gauge_speed.set_value(speed)
            if temp is not None:
                self.gauge_temp.set_value(temp)
        # ...existing code...

    def init_ui(self):
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from main import get_makes_and_models
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.setMinimumSize(900, 600)
        self.setWindowTitle("Scanner OBD2 Premium")
        self._vehicle_catalog = get_makes_and_models()
        self.label_status = QLabel("Estado: Desconectado")
        self.label_status.setStyleSheet("font-weight: bold; color: red; margin-bottom: 8px;")
        main_layout.addWidget(self.label_status)
        btns_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar ELM327")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setVisible(True)
        self.btn_read_vin = QPushButton("Leer VIN")
        self.btn_read_vin.setObjectName("btn_read_vin")
        self.btn_scan_protocols = QPushButton("Escanear Protocolos")
        self.btn_scan_protocols.setObjectName("btn_scan_protocols")
        self.btn_scan_pids = QPushButton("Buscar PIDs")
        self.btn_scan_pids.setObjectName("btn_scan_pids")
        self.btn_scan_pids.setVisible(True)
        btns_layout.addWidget(self.btn_connect)
        btns_layout.addWidget(self.btn_read_vin)
        btns_layout.addWidget(self.btn_scan_protocols)
        main_layout.addLayout(btns_layout)
        self.le_vin = QLineEdit()
        self.le_vin.setReadOnly(True)
        main_layout.addWidget(QLabel("VIN:"))
        main_layout.addWidget(self.le_vin)
        self.le_protocol = QLineEdit()
        self.le_protocol.setReadOnly(True)
        main_layout.addWidget(QLabel("Protocolo:"))
        main_layout.addWidget(self.le_protocol)
        self.btn_start_live = QPushButton("Iniciar lectura")
        self.btn_start_live.setObjectName("btn_start_live")
        self.pid_selector = QComboBox()
        self.label_pid_value = QLabel("Esperando datos...")
        main_layout.addWidget(self.btn_scan_pids)
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
        self.btn_start_stream.setObjectName("btn_start_stream")
        layout_pids.addWidget(self.btn_start_stream)
        self.values_layout = QVBoxLayout()
        layout_pids.addLayout(self.values_layout)
        self.tabs.addTab(self.tab_pids, "PIDs múltiples")
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
        # --- NUEVA PESTAÑA DIAGNÓSTICO ---
        self.tab_diagnostico = QWidget()
        diag_layout = QVBoxLayout(self.tab_diagnostico)
        self.btn_read_dtcs = QPushButton("Leer DTCs")
        self.btn_read_dtcs.setObjectName("btn_read_dtcs")
        self.btn_clear_dtcs = QPushButton("Borrar DTCs")
        self.btn_clear_dtcs.setObjectName("btn_clear_dtcs")
        btns_diag = QHBoxLayout()
        btns_diag.addWidget(self.btn_read_dtcs)
        btns_diag.addWidget(self.btn_clear_dtcs)
        diag_layout.addLayout(btns_diag)
        self.dtcs_list_label = QLabel("Estado: No conectado")
        diag_layout.addWidget(self.dtcs_list_label)
        self.dtcs_list = QListWidget()
        diag_layout.addWidget(self.dtcs_list)
        self.tab_diagnostico.setLayout(diag_layout)
        self.tabs.addTab(self.tab_diagnostico, "Diagnóstico")
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
        # self.pid_search.textChanged.connect(self.filtrar_pid_list)  # Corrección: eliminar conexión a método inexistente
        # --- Sección decodificación VIN ---
        vin_section = QGroupBox("Decodificación de VIN")
        vin_layout = QVBoxLayout()
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Ingrese VIN (17 caracteres)")
        self.vin_button = QPushButton("Decodificar VIN")
        self.vin_button.setObjectName("vin_button")
        self.vin_output = QTextEdit()
        self.vin_output.setReadOnly(True)
        vin_layout.addWidget(QLabel("VIN:"))
        vin_layout.addWidget(self.vin_input)
        vin_layout.addWidget(self.vin_button)
        vin_layout.addWidget(self.vin_output)
        vin_section.setLayout(vin_layout)
        main_layout.addWidget(vin_section)
        self.vin_button.clicked.connect(self.decodificar_vin)
        # --- Limpieza de botones sin funcionalidad ---
        self._limpiar_botones_obsoletos()

        # --- Conexión del buscador de PIDs ---
        self.pid_search.textChanged.connect(self._filtrar_pid_list)

        # --- Conexión del botón de stream multipid ---
        self.btn_start_stream.clicked.connect(self._emitir_iniciar_stream)

        # Conexión de botones de diagnóstico al controlador si está disponible
        if hasattr(self, 'controller') and self.controller is not None:
            self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
            self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

    def set_controller(self, controller):
        """Permite asignar el controlador OBDController a la instancia y conectar los botones de diagnóstico."""
        self.controller = controller
        self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
        self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

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
        # Actualizar gauges realistas si existen datos
        rpm = self.last_pid_values.get('RPM')
        speed = self.last_pid_values.get('Velocidad')
        temp = self.last_pid_values.get('Temp Agua')
        if hasattr(self, 'gauge_rpm'):
            if rpm is not None:
                self.gauge_rpm.set_value(rpm)
            if speed is not None:
                self.gauge_speed.set_value(speed)
            if temp is not None:
                self.gauge_temp.set_value(temp)
        # ...existing code...

    def init_ui(self):
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from main import get_makes_and_models
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.setMinimumSize(900, 600)
        self.setWindowTitle("Scanner OBD2 Premium")
        self._vehicle_catalog = get_makes_and_models()
        self.label_status = QLabel("Estado: Desconectado")
        self.label_status.setStyleSheet("font-weight: bold; color: red; margin-bottom: 8px;")
        main_layout.addWidget(self.label_status)
        btns_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar ELM327")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setVisible(True)
        self.btn_read_vin = QPushButton("Leer VIN")
        self.btn_read_vin.setObjectName("btn_read_vin")
        self.btn_scan_protocols = QPushButton("Escanear Protocolos")
        self.btn_scan_protocols.setObjectName("btn_scan_protocols")
        self.btn_scan_pids = QPushButton("Buscar PIDs")
        self.btn_scan_pids.setObjectName("btn_scan_pids")
        self.btn_scan_pids.setVisible(True)
        btns_layout.addWidget(self.btn_connect)
        btns_layout.addWidget(self.btn_read_vin)
        btns_layout.addWidget(self.btn_scan_protocols)
        main_layout.addLayout(btns_layout)
        self.le_vin = QLineEdit()
        self.le_vin.setReadOnly(True)
        main_layout.addWidget(QLabel("VIN:"))
        main_layout.addWidget(self.le_vin)
        self.le_protocol = QLineEdit()
        self.le_protocol.setReadOnly(True)
        main_layout.addWidget(QLabel("Protocolo:"))
        main_layout.addWidget(self.le_protocol)
        self.btn_start_live = QPushButton("Iniciar lectura")
        self.btn_start_live.setObjectName("btn_start_live")
        self.pid_selector = QComboBox()
        self.label_pid_value = QLabel("Esperando datos...")
        main_layout.addWidget(self.btn_scan_pids)
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
        self.btn_start_stream.setObjectName("btn_start_stream")
        layout_pids.addWidget(self.btn_start_stream)
        self.values_layout = QVBoxLayout()
        layout_pids.addLayout(self.values_layout)
        self.tabs.addTab(self.tab_pids, "PIDs múltiples")
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
        # --- NUEVA PESTAÑA DIAGNÓSTICO ---
        self.tab_diagnostico = QWidget()
        diag_layout = QVBoxLayout(self.tab_diagnostico)
        self.btn_read_dtcs = QPushButton("Leer DTCs")
        self.btn_read_dtcs.setObjectName("btn_read_dtcs")
        self.btn_clear_dtcs = QPushButton("Borrar DTCs")
        self.btn_clear_dtcs.setObjectName("btn_clear_dtcs")
        btns_diag = QHBoxLayout()
        btns_diag.addWidget(self.btn_read_dtcs)
        btns_diag.addWidget(self.btn_clear_dtcs)
        diag_layout.addLayout(btns_diag)
        self.dtcs_list_label = QLabel("Estado: No conectado")
        diag_layout.addWidget(self.dtcs_list_label)
        self.dtcs_list = QListWidget()
        diag_layout.addWidget(self.dtcs_list)
        self.tab_diagnostico.setLayout(diag_layout)
        self.tabs.addTab(self.tab_diagnostico, "Diagnóstico")
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
        # self.pid_search.textChanged.connect(self.filtrar_pid_list)  # Corrección: eliminar conexión a método inexistente
        # --- Sección decodificación VIN ---
        vin_section = QGroupBox("Decodificación de VIN")
        vin_layout = QVBoxLayout()
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Ingrese VIN (17 caracteres)")
        self.vin_button = QPushButton("Decodificar VIN")
        self.vin_button.setObjectName("vin_button")
        self.vin_output = QTextEdit()
        self.vin_output.setReadOnly(True)
        vin_layout.addWidget(QLabel("VIN:"))
        vin_layout.addWidget(self.vin_input)
        vin_layout.addWidget(self.vin_button)
        vin_layout.addWidget(self.vin_output)
        vin_section.setLayout(vin_layout)
        main_layout.addWidget(vin_section)
        self.vin_button.clicked.connect(self.decodificar_vin)
        # --- Limpieza de botones sin funcionalidad ---
        self._limpiar_botones_obsoletos()

        # --- Conexión del buscador de PIDs ---
        self.pid_search.textChanged.connect(self._filtrar_pid_list)

        # --- Conexión del botón de stream multipid ---
        self.btn_start_stream.clicked.connect(self._emitir_iniciar_stream)

        # Conexión de botones de diagnóstico al controlador si está disponible
        if hasattr(self, 'controller') and self.controller is not None:
            self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
            self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

    def set_controller(self, controller):
        """Permite asignar el controlador OBDController a la instancia y conectar los botones de diagnóstico."""
        self.controller = controller
        self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
        self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

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
        # Actualizar gauges realistas si existen datos
        rpm = self.last_pid_values.get('RPM')
        speed = self.last_pid_values.get('Velocidad')
        temp = self.last_pid_values.get('Temp Agua')
        if hasattr(self, 'gauge_rpm'):
            if rpm is not None:
                self.gauge_rpm.set_value(rpm)
            if speed is not None:
                self.gauge_speed.set_value(speed)
            if temp is not None:
                self.gauge_temp.set_value(temp)
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
        # Solo detener timers y limpiar recursos
        self.stop_graph_timer()
        super().closeEvent(a0)

    def cargar_pids_agrupados_en_lista(self, supported_cmds):
        # Limpiar la lista multipid
        self.pid_list.clear()
        # Ordenar los comandos por nombre para mejor UX
        sorted_cmds = sorted(supported_cmds, key=lambda c: c.name)
        for cmd in sorted_cmds:
            if cmd is not None:
                item = QListWidgetItem(cmd.name)
                item.setData(Qt.ItemDataRole.UserRole, cmd)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.pid_list.addItem(item)
        self.set_status(f"{len(sorted_cmds)} PIDs cargados en multipid")

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
                # Para QComboBox, solo se puede añadir texto y opcionalmente userData
                self.pid_selector.addItem(f"{cmd.name} ({cmd.command})", cmd)
            # Seleccionar automáticamente algunos PIDs comunes
            for cmd in [obd.commands['RPM'], obd.commands['SPEED'], obd.commands['ENGINE_LOAD']]:
                if cmd in cmds:
                    index = self.pid_selector.findData(cmd, Qt.ItemDataRole.UserRole)
                    if index != -1:
                        self.pid_selector.setCurrentIndex(index)
        # Eliminar lógica de add_obd_command en async_pid_finder
        self.async_pid_finder.start()

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

    def clear_gauges(self):
        # Limpia cualquier layout de gauges si existe (para compatibilidad con stop_pid_stream)
        if hasattr(self, 'values_layout') and self.values_layout is not None:
            layout = self.values_layout
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if w:
                    w.deleteLater()
        # También limpiar gauges en tuning_widget si existe
        if hasattr(self, 'tuning_widget') and hasattr(self.tuning_widget, 'gauge_layout'):
            layout = self.tuning_widget.gauge_layout
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if w:
                    w.deleteLater()

    def decodificar_vin(self):
        vin = self.vin_input.text().strip()
        decoder = VinDecoder()
        info = decoder.decode(vin)
        if not info.get('valido', False):
            QMessageBox.warning(self, "VIN inválido", info.get('error', 'Error desconocido'))
            self.vin_output.setText("")
            return
        texto = f"""
VIN: {info['vin']}
País: {info['pais']}
Fabricante: {info['fabricante']}
Año: {info['anio']}
Planta: {info['planta']}
Secuencia: {info['secuencia']}
Dígito control: {info['digito_control']} ({'OK' if info['digito_control_ok'] else 'NO COINCIDE'})
VIN válido: Sí
"""
        self.vin_output.setText(texto)

    def _limpiar_botones_obsoletos(self):
        # Elimina QPushButton que no sean funcionales ni estén en la lista permitida
        permitidos = {'vin_button', 'btn_connect', 'btn_read_vin', 'btn_scan_protocols', 'btn_scan_pids', 'btn_start_live', 'btn_start_stream', 'btn_read_dtcs', 'btn_clear_dtcs'}
        for widget in self.findChildren(QPushButton):
            if widget.objectName() not in permitidos and not widget.signalsBlocked():
                widget.setVisible(False)
                widget.setParent(None)
        # Opcional: limpiar otros widgets obsoletos aquí

    def _filtrar_pid_list(self, texto):
        """Filtra la lista de PIDs multipid en tiempo real según el texto del buscador"""
        texto = texto.lower().strip()
        for i in range(self.pid_list.count()):
            item = self.pid_list.item(i)
            visible = texto in item.text().lower()
            item.setHidden(not visible)

    def _emitir_iniciar_stream(self):
        """Llama al método del backend/controlador para iniciar el stream multipid"""
        # Si tienes un backend/controlador, llama su método aquí
        if self.backend is not None and hasattr(self.backend, 'iniciar_stream_pids'):
            self.backend.iniciar_stream_pids()
        else:
            self.show_message("Info", "Iniciar stream multipid (conectar con backend)")
    def init_ui(self):
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from main import get_makes_and_models
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.setMinimumSize(900, 600)
        self.setWindowTitle("Scanner OBD2 Premium")
        self._vehicle_catalog = get_makes_and_models()
        self.label_status = QLabel("Estado: Desconectado")
        self.label_status.setStyleSheet("font-weight: bold; color: red; margin-bottom: 8px;")
        main_layout.addWidget(self.label_status)
        btns_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar ELM327")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setVisible(True)
        self.btn_read_vin = QPushButton("Leer VIN")
        self.btn_read_vin.setObjectName("btn_read_vin")
        self.btn_scan_protocols = QPushButton("Escanear Protocolos")
        self.btn_scan_protocols.setObjectName("btn_scan_protocols")
        self.btn_scan_pids = QPushButton("Buscar PIDs")
        self.btn_scan_pids.setObjectName("btn_scan_pids")
        self.btn_scan_pids.setVisible(True)
        btns_layout.addWidget(self.btn_connect)
        btns_layout.addWidget(self.btn_read_vin)
        btns_layout.addWidget(self.btn_scan_protocols)
        main_layout.addLayout(btns_layout)
        self.le_vin = QLineEdit()
        self.le_vin.setReadOnly(True)
        main_layout.addWidget(QLabel("VIN:"))
        main_layout.addWidget(self.le_vin)
        self.le_protocol = QLineEdit()
        self.le_protocol.setReadOnly(True)
        main_layout.addWidget(QLabel("Protocolo:"))
        main_layout.addWidget(self.le_protocol)
        self.btn_start_live = QPushButton("Iniciar lectura")
        self.btn_start_live.setObjectName("btn_start_live")
        self.pid_selector = QComboBox()
        self.label_pid_value = QLabel("Esperando datos...")
        main_layout.addWidget(self.btn_scan_pids)
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
        self.btn_start_stream.setObjectName("btn_start_stream")
        layout_pids.addWidget(self.btn_start_stream)
        self.values_layout = QVBoxLayout()
        layout_pids.addLayout(self.values_layout)
        self.tabs.addTab(self.tab_pids, "PIDs múltiples")
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
        # --- NUEVA PESTAÑA DIAGNÓSTICO ---
        self.tab_diagnostico = QWidget()
        diag_layout = QVBoxLayout(self.tab_diagnostico)
        self.btn_read_dtcs = QPushButton("Leer DTCs")
        self.btn_read_dtcs.setObjectName("btn_read_dtcs")
        self.btn_clear_dtcs = QPushButton("Borrar DTCs")
        self.btn_clear_dtcs.setObjectName("btn_clear_dtcs")
        btns_diag = QHBoxLayout()
        btns_diag.addWidget(self.btn_read_dtcs)
        btns_diag.addWidget(self.btn_clear_dtcs)
        diag_layout.addLayout(btns_diag)
        self.dtcs_list_label = QLabel("Estado: No conectado")
        diag_layout.addWidget(self.dtcs_list_label)
        self.dtcs_list = QListWidget()
        diag_layout.addWidget(self.dtcs_list)
        self.tab_diagnostico.setLayout(diag_layout)
        self.tabs.addTab(self.tab_diagnostico, "Diagnóstico")
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
        # self.pid_search.textChanged.connect(self.filtrar_pid_list)  # Corrección: eliminar conexión a método inexistente
        # --- Sección decodificación VIN ---
        vin_section = QGroupBox("Decodificación de VIN")
        vin_layout = QVBoxLayout()
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Ingrese VIN (17 caracteres)")
        self.vin_button = QPushButton("Decodificar VIN")
        self.vin_button.setObjectName("vin_button")
        self.vin_output = QTextEdit()
        self.vin_output.setReadOnly(True)
        vin_layout.addWidget(QLabel("VIN:"))
        vin_layout.addWidget(self.vin_input)
        vin_layout.addWidget(self.vin_button)
        vin_layout.addWidget(self.vin_output)
        vin_section.setLayout(vin_layout)
        main_layout.addWidget(vin_section)
        self.vin_button.clicked.connect(self.decodificar_vin)
        # --- Limpieza de botones sin funcionalidad ---
        self._limpiar_botones_obsoletos()

        # --- Conexión del buscador de PIDs ---
        self.pid_search.textChanged.connect(self._filtrar_pid_list)

        # --- Conexión del botón de stream multipid ---
        self.btn_start_stream.clicked.connect(self._emitir_iniciar_stream)

        # Conexión de botones de diagnóstico al controlador si está disponible
        if hasattr(self, 'controller') and self.controller is not None:
            self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
            self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

    def set_controller(self, controller):
        """Permite asignar el controlador OBDController a la instancia y conectar los botones de diagnóstico."""
        self.controller = controller
        self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
        self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

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
        # Actualizar gauges realistas si existen datos
        rpm = self.last_pid_values.get('RPM')
        speed = self.last_pid_values.get('Velocidad')
        temp = self.last_pid_values.get('Temp Agua')
        if hasattr(self, 'gauge_rpm'):
            if rpm is not None:
                self.gauge_rpm.set_value(rpm)
            if speed is not None:
                self.gauge_speed.set_value(speed)
            if temp is not None:
                self.gauge_temp.set_value(temp)
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
        # Solo detener timers y limpiar recursos
        self.stop_graph_timer()
        super().closeEvent(a0)

    def cargar_pids_agrupados_en_lista(self, supported_cmds):
        # Limpiar la lista multipid
        self.pid_list.clear()
        # Ordenar los comandos por nombre para mejor UX
        sorted_cmds = sorted(supported_cmds, key=lambda c: c.name)
        for cmd in sorted_cmds:
            if cmd is not None:
                item = QListWidgetItem(cmd.name)
                item.setData(Qt.ItemDataRole.UserRole, cmd)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.pid_list.addItem(item)
        self.set_status(f"{len(sorted_cmds)} PIDs cargados en multipid")

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
                # Para QComboBox, solo se puede añadir texto y opcionalmente userData
                self.pid_selector.addItem(f"{cmd.name} ({cmd.command})", cmd)
            # Seleccionar automáticamente algunos PIDs comunes
            for cmd in [obd.commands['RPM'], obd.commands['SPEED'], obd.commands['ENGINE_LOAD']]:
                if cmd in cmds:
                    index = self.pid_selector.findData(cmd, Qt.ItemDataRole.UserRole)
                    if index != -1:
                        self.pid_selector.setCurrentIndex(index)
        # Eliminar lógica de add_obd_command en async_pid_finder
        self.async_pid_finder.start()

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

    def clear_gauges(self):
        # Limpia cualquier layout de gauges si existe (para compatibilidad con stop_pid_stream)
        if hasattr(self, 'values_layout') and self.values_layout is not None:
            layout = self.values_layout
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if w:
                    w.deleteLater()
        # También limpiar gauges en tuning_widget si existe
        if hasattr(self, 'tuning_widget') and hasattr(self.tuning_widget, 'gauge_layout'):
            layout = self.tuning_widget.gauge_layout
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if w:
                    w.deleteLater()

    def decodificar_vin(self):
        vin = self.vin_input.text().strip()
        decoder = VinDecoder()
        info = decoder.decode(vin)
        if not info.get('valido', False):
            QMessageBox.warning(self, "VIN inválido", info.get('error', 'Error desconocido'))
            self.vin_output.setText("")
            return
        texto = f"""
VIN: {info['vin']}
País: {info['pais']}
Fabricante: {info['fabricante']}
Año: {info['anio']}
Planta: {info['planta']}
Secuencia: {info['secuencia']}
Dígito control: {info['digito_control']} ({'OK' if info['digito_control_ok'] else 'NO COINCIDE'})
VIN válido: Sí
"""
        self.vin_output.setText(texto)

    def _limpiar_botones_obsoletos(self):
        # Elimina QPushButton que no sean funcionales ni estén en la lista permitida
        permitidos = {'vin_button', 'btn_connect', 'btn_read_vin', 'btn_scan_protocols', 'btn_scan_pids', 'btn_start_live', 'btn_start_stream', 'btn_read_dtcs', 'btn_clear_dtcs'}
        for widget in self.findChildren(QPushButton):
            if widget.objectName() not in permitidos and not widget.signalsBlocked():
                widget.setVisible(False)
                widget.setParent(None)
       
    def _filtrar_pid_list(self, texto):
        """Filtra la lista de PIDs multipid en tiempo real según el texto del buscador"""
        texto = texto.lower().strip()
        for i in range(self.pid_list.count()):
            item = self.pid_list.item(i)
            visible = texto in item.text().lower()
            item.setHidden(not visible)

    def _emitir_iniciar_stream(self):
        """Llama al método del backend/controlador para iniciar el stream multipid"""
        # Si tienes un backend/controlador, llama su método aquí
        if self.backend is not None and hasattr(self.backend, 'iniciar_stream_pids'):
            self.backend.iniciar_stream_pids()
        else:
            self.show_message("Info", "Iniciar stream multipid (conectar con backend)")
    def init_ui(self):
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from main import get_makes_and_models
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.setMinimumSize(900, 600)
        self.setWindowTitle("Scanner OBD2 Premium")
        self._vehicle_catalog = get_makes_and_models()
        self.label_status = QLabel("Estado: Desconectado")
        self.label_status.setStyleSheet("font-weight: bold; color: red; margin-bottom: 8px;")
        main_layout.addWidget(self.label_status)
        btns_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar ELM327")
        self.btn_connect.setObjectName("btn_connect")
        self.btn_connect.setVisible(True)
        self.btn_read_vin = QPushButton("Leer VIN")
        self.btn_read_vin.setObjectName("btn_read_vin")
        self.btn_scan_protocols = QPushButton("Escanear Protocolos")
        self.btn_scan_protocols.setObjectName("btn_scan_protocols")
        self.btn_scan_pids = QPushButton("Buscar PIDs")
        self.btn_scan_pids.setObjectName("btn_scan_pids")
        self.btn_scan_pids.setVisible(True)
        btns_layout.addWidget(self.btn_connect)
        btns_layout.addWidget(self.btn_read_vin)
        btns_layout.addWidget(self.btn_scan_protocols)
        main_layout.addLayout(btns_layout)
        self.le_vin = QLineEdit()
        self.le_vin.setReadOnly(True)
        main_layout.addWidget(QLabel("VIN:"))
        main_layout.addWidget(self.le_vin)
        self.le_protocol = QLineEdit()
        self.le_protocol.setReadOnly(True)
        main_layout.addWidget(QLabel("Protocolo:"))
        main_layout.addWidget(self.le_protocol)
        self.btn_start_live = QPushButton("Iniciar lectura")
        self.btn_start_live.setObjectName("btn_start_live")
        self.pid_selector = QComboBox()
        self.label_pid_value = QLabel("Esperando datos...")
        main_layout.addWidget(self.btn_scan_pids)
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
        self.btn_start_stream.setObjectName("btn_start_stream")
        layout_pids.addWidget(self.btn_start_stream)
        self.values_layout = QVBoxLayout()
        layout_pids.addLayout(self.values_layout)
        self.tabs.addTab(self.tab_pids, "PIDs múltiples")
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
        # --- NUEVA PESTAÑA DIAGNÓSTICO ---
        self.tab_diagnostico = QWidget()
        diag_layout = QVBoxLayout(self.tab_diagnostico)
        self.btn_read_dtcs = QPushButton("Leer DTCs")
        self.btn_read_dtcs.setObjectName("btn_read_dtcs")
        self.btn_clear_dtcs = QPushButton("Borrar DTCs")
        self.btn_clear_dtcs.setObjectName("btn_clear_dtcs")
        btns_diag = QHBoxLayout()
        btns_diag.addWidget(self.btn_read_dtcs)
        btns_diag.addWidget(self.btn_clear_dtcs)
        diag_layout.addLayout(btns_diag)
        self.dtcs_list_label = QLabel("Estado: No conectado")
        diag_layout.addWidget(self.dtcs_list_label)
        self.dtcs_list = QListWidget()
        diag_layout.addWidget(self.dtcs_list)
        self.tab_diagnostico.setLayout(diag_layout)
        self.tabs.addTab(self.tab_diagnostico, "Diagnóstico")
        # --- NUEVA PESTAÑA GAUGES 2.0 ---
        self.tab_gauges = QWidget()
        gauges_layout = QHBoxLayout(self.tab_gauges)
        self.gauge_rpm = RealisticGaugeWidget("RPM", 0, 8000, "rpm", QColor("#00eaff"))
        self.gauge_speed = RealisticGaugeWidget("Velocidad", 0, 240, "km/h", QColor("#ffb300"))
        self.gauge_temp = RealisticGaugeWidget("Temp Agua", 40, 120, "°C", QColor("#e91e63"))
        gauges_layout.addWidget(self.gauge_rpm)
        gauges_layout.addWidget(self.gauge_speed)
        gauges_layout.addWidget(self.gauge_temp)
        self.tabs.addTab(self.tab_gauges, "GAUGES 2.0")
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
        # self.pid_search.textChanged.connect(self.filtrar_pid_list)  # Corrección: eliminar conexión a método inexistente
        # --- Sección decodificación VIN ---
        vin_section = QGroupBox("Decodificación de VIN")
        vin_layout = QVBoxLayout()
        self.vin_input = QLineEdit()
        self.vin_input.setPlaceholderText("Ingrese VIN (17 caracteres)")
        self.vin_button = QPushButton("Decodificar VIN")
        self.vin_button.setObjectName("vin_button")
        self.vin_output = QTextEdit()
        self.vin_output.setReadOnly(True)
        vin_layout.addWidget(QLabel("VIN:"))
        vin_layout.addWidget(self.vin_input)
        vin_layout.addWidget(self.vin_button)
        vin_layout.addWidget(self.vin_output)
        vin_section.setLayout(vin_layout)
        main_layout.addWidget(vin_section)
        self.vin_button.clicked.connect(self.decodificar_vin)
        # --- Limpieza de botones sin funcionalidad ---
        self._limpiar_botones_obsoletos()

        # --- Conexión del buscador de PIDs ---
        self.pid_search.textChanged.connect(self._filtrar_pid_list)

        # --- Conexión del botón de stream multipid ---
        self.btn_start_stream.clicked.connect(self._emitir_iniciar_stream)

        # Conexión de botones de diagnóstico al controlador si está disponible
        if hasattr(self, 'controller') and self.controller is not None:
            self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
            self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

    def set_controller(self, controller):
        """Permite asignar el controlador OBDController a la instancia y conectar los botones de diagnóstico."""
        self.controller = controller
        self.btn_read_dtcs.clicked.connect(self.controller.leer_dtcs)
        self.btn_clear_dtcs.clicked.connect(self.controller.borrar_dtcs)

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
        # Actualizar gauges realistas si existen datos
        rpm = self.last_pid_values.get('RPM')
        speed = self.last_pid_values.get('Velocidad')
        temp = self.last_pid_values.get('Temp Agua')
        if hasattr(self, 'gauge_rpm'):
            if rpm is not None:
                self.gauge_rpm.set_value(rpm)
            if speed is not None:
                self.gauge_speed.set_value(speed)
            if temp is not None:
                self.gauge_temp.set_value(temp)
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
        # Solo detener timers y limpiar recursos
        self.stop_graph_timer()
        super().closeEvent(a0)

    def cargar_pids_agrupados_en_lista(self, supported_cmds):
        # Limpiar la lista multipid
        self.pid_list.clear()
        # Ordenar los comandos por nombre para mejor UX
        sorted_cmds = sorted(supported_cmds, key=lambda c: c.name)
        for cmd in sorted_cmds:
            if cmd is not None:
                item = QListWidgetItem(cmd.name)
                item.setData(Qt.ItemDataRole.UserRole, cmd)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.pid_list.addItem(item)
        self.set_status(f"{len(sorted_cmds)} PIDs cargados en multipid")

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
                # Para QComboBox, solo se puede añadir texto y opcionalmente userData
                self.pid_selector.addItem(f"{cmd.name} ({cmd.command})", cmd)
            # Seleccionar automáticamente algunos PIDs comunes
            for cmd in [obd.commands['RPM'], obd.commands['SPEED'], obd.commands['ENGINE_LOAD']]:
                if cmd in cmds:
                    index = self.pid_selector.findData(cmd, Qt.ItemDataRole.UserRole)
                    if index != -1:
                        self.pid_selector.setCurrentIndex(index)
        # Eliminar lógica de add_obd_command en async_pid_finder
        self.async_pid_finder.start()

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

    def clear_gauges(self):
        # Limpia cualquier layout de gauges si existe (para compatibilidad con stop_pid_stream)
        if hasattr(self, 'values_layout') and self.values_layout is not None:
            layout = self.values_layout
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if w:
                    w.deleteLater()
        # También limpiar gauges en tuning_widget si existe
        if hasattr(self, 'tuning_widget') and hasattr(self.tuning_widget, 'gauge_layout'):
            layout = self.tuning_widget.gauge_layout
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if w:
                    w.deleteLater()

    def decodificar_vin(self):
        vin = self.vin_input.text().strip()
        decoder = VinDecoder()
        info = decoder.decode(vin)
        if not info.get('valido', False):
            QMessageBox.warning(self, "VIN inválido", info.get('error', 'Error desconocido'))
            self.vin_output.setText("")
            return
        texto = f"""
VIN: {info['vin']}
País: {info['pais']}
Fabricante: {info['fabricante']}
Año: {info['anio']}
Planta: {info['planta']}
Secuencia: {info['secuencia']}
Dígito control: {info['digito_control']} ({'OK' if info['digito_control_ok'] else 'NO COINCIDE'})
VIN válido: Sí
"""
        self.vin_output.setText(texto)

    def _limpiar_botones_obsoletos(self):
        # Elimina QPushButton que no sean funcionales ni estén en la lista permitida
        permitidos = {'vin_button', 'btn_connect', 'btn_read_vin', 'btn_scan_protocols', 'btn_scan_pids', 'btn_start_live', 'btn_start_stream', 'btn_read_dtcs', 'btn_clear_dtcs'}
        for widget in self.findChildren(QPushButton):
            if widget.objectName() not in permitidos and not widget.signalsBlocked():
                widget.setVisible(False)
                widget.setParent(None)
        # Opcional: limpiar otros widgets obsoletos aquí

    def _filtrar_pid_list(self, texto):
        """Filtra la lista de PIDs multipid en tiempo real según el texto del buscador"""
        texto = texto.lower().strip()
        for i in range(self.pid_list.count()):
            item = self.pid_list.item(i)
            visible = texto in item.text().lower()
            item.setHidden(not visible)

    def _emitir_iniciar_stream(self):
        """Llama al método del backend/controlador para iniciar el stream multipid"""
        # Si tienes un backend/controlador, llama su método aquí
        if self.backend is not None and hasattr(self.backend, 'iniciar_stream_pids'):
            self.backend.iniciar_stream_pids()
        else:
            self.show_message("Info", "Iniciar stream multipid (conectar con backend)")