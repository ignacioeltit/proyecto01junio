"""
data_visualizer.py - Interfaz gráfica simple para visualizar datos OBD-II en tiempo real
"""
import sys
import os
import importlib.util
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

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QLineEdit, QGroupBox, QFormLayout, QCheckBox, QTabWidget, QHBoxLayout, QSizePolicy, QFrame, QComboBox, QMessageBox, QInputDialog, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFileDialog
import importlib.util
import os
from PyQt6.QtCore import QTimer, Qt, QPointF, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QRadialGradient
import math
import functools

GAUGE_COLORS = [
    '#00bcd4', '#ff9800', '#e91e63', '#4caf50', '#ffeb3b', '#9c27b0', '#f44336', '#3f51b5', '#8bc34a', '#607d8b'
]

def get_gauge_color(idx):
    return QColor(GAUGE_COLORS[idx % len(GAUGE_COLORS)])

class CanSignalViewer(QWidget):
    """
    Widget para visualizar señales CAN decodificadas en una tabla.
    """
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

class DataVisualizer(QWidget):
    def on_confirm_gauges(self):
        if not self.elm327 or not getattr(self.elm327, 'connected', False):
            QMessageBox.warning(self, "No conectado", "Debes conectar el dispositivo antes de seleccionar gauges.")
            return
        selected = [pid for pid, cb in self.gauge_checkboxes.items() if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "Sin selección", "Debes seleccionar al menos un PID para mostrar como gauge.")
            return
        soportados = set(self.scan_supported_pids_for_gauges())
        no_soportados = [pid for pid in selected if pid not in soportados]
        if no_soportados:
            QMessageBox.warning(self, "PIDs no soportados", f"Los siguientes PIDs no están soportados: {', '.join(no_soportados)}")
            return
        self.selected_pids = set(selected)
        self.populate_gauges_tab()
        self.tabs.setCurrentWidget(self.gauges_tab)

    def scan_supported_pids_for_gauges(self):
        if hasattr(self, 'supported_pids') and self.supported_pids:
            return self.supported_pids
        if self.elm327 and hasattr(self.elm327, 'query'):
            resp = self.elm327.query('0100')
            try:
                parts = resp.replace('\r', ' ').replace('\n', ' ').split()
                idx = parts.index("41") if "41" in parts else -1
                if idx != -1 and len(parts) > idx+5:
                    supported = int("".join(parts[idx+2:idx+6]), 16)
                    base = 0x00
                    result = []
                    for i in range(32):
                        if supported & (1 << (31-i)):
                            pid = f"01{base+i:02X}"
                            result.append(pid)
                    return result
            except Exception:
                pass
        return [normalizar_pid(pid) for pid in PIDS.keys()]

    def populate_gauges_tab(self):
        for i in reversed(range(self.gauges_content_layout.count())):
            item = self.gauges_content_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget:
                widget.setParent(None)
        self.gauge_widgets.clear()
        for idx, pid in enumerate(self.selected_pids):
            info = self.pid_manager.get_pid_info(pid) if self.pid_manager else PIDS.get(pid, {})
            name = info.get("desc", pid)
            min_v = info.get("min", 0)
            max_v = info.get("max", 100)
            unit = info.get("unidades", "")
            import sys, os, importlib.util
            gauge_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../src/ui/widgets/gauge.py'))
            spec = importlib.util.spec_from_file_location('GaugeWidget', gauge_path)
            if spec and spec.loader:
                gauge_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(gauge_mod)
                GaugeWidget = gauge_mod.GaugeWidget
            else:
                raise ImportError('No se pudo cargar GaugeWidget')
            gauge = GaugeWidget(min_value=min_v, max_value=max_v, units=unit, color=get_gauge_color(idx))
            self.gauge_widgets[pid] = gauge
            gauge_container = QWidget()
            vlayout = QVBoxLayout()
            vlayout.setContentsMargins(0, 0, 0, 0)
            vlayout.setSpacing(2)
            label_widget = QLabel(name)
            label_widget.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            label_widget.setStyleSheet("color: #111; font-weight: bold; font-size: 18px; padding: 2px 0 6px 0;")
            vlayout.addWidget(label_widget)
            vlayout.addWidget(gauge)
            gauge_container.setLayout(vlayout)
            self.gauges_content_layout.addWidget(gauge_container)

    def __init__(self, get_data_fn, pid_manager=None, elm327=None):
        super().__init__()
        self.get_data_fn = get_data_fn
        self.pid_manager = pid_manager
        self.elm327 = elm327
        self.labels = {}
        self.checkboxes = {}
        self.selected_pids = set()
        self.filter_text = ""
        self.gauge_widgets = {}  # Inicialización correcta aquí
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(500)
        # Modo de identificación: 0=VIN, 1=Manual, 2=Genérico
        self.vehicle_id_mode = 0
        self.vehicle_info = {}
        self.init_ui()

    def scan_supported_pids(self):
        """Escanea automáticamente los PIDs soportados usando ELM327 y actualiza la lista en la GUI."""
        if not self.elm327 or not hasattr(self.elm327, 'query'):
            # Si no hay conexión real, usar todos los PIDs
            self.supported_pids = [normalizar_pid(pid) for pid in PIDS.keys()]
            return
        soportados = set()
        for base in [0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xE0]:
            cmd = f"01 {base:02X}"
            respuesta = self.elm327.query(cmd)
            if not respuesta:
                break
            # Buscar los bytes hexadecimales en la respuesta (ej: '41 00 BE 3E B8 13')
            partes = respuesta.strip().split()
            if len(partes) < 6:
                break
            bytes_hex = ''.join(partes[2:6])
            if len(bytes_hex) != 8:
                break
            bits = bin(int(bytes_hex, 16))[2:].zfill(32)
            for i, bit in enumerate(bits):
                if bit == '1':
                    pid = base + i + 1
                    soportados.add(f"{pid:02X}")
            # Si el primer bit es 0, no hay más bloques
            if bits[0] == '0':
                break
        self.supported_pids = [pid for pid in [normalizar_pid(pid) for pid in PIDS.keys()] if pid in soportados]

    def init_ui(self):
        self.tabs = QTabWidget()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tabs)
        # Selector de identificación
        self.id_selector = QComboBox()
        self.id_selector.addItems([
            "Escaneo automático VIN",
            "Selección manual",
            "Lectura Genérica (solo estándar)"
        ])
        self.id_selector.currentIndexChanged.connect(self.on_id_mode_changed)
        main_layout.insertWidget(0, self.id_selector)
        # --- Pestaña de conexión ---
        self.conn_tab = QWidget()
        conn_layout = QVBoxLayout(self.conn_tab)
        # Estado y parámetros de conexión
        self.conn_status = QLabel("Estado: Conectado")
        self.conn_status.setAlignment(Qt.AlignmentFlag.AlignLeft)
        conn_layout.addWidget(self.conn_status)
        self.conn_params = QLabel()
        self.update_conn_params()
        conn_layout.addWidget(self.conn_params)
        # VIN
        self.vin_label = QLabel("VIN: ...")
        conn_layout.addWidget(self.vin_label)
        # Botón para leer VIN manualmente
        self.btn_read_vin = QPushButton("Leer VIN")
        self.btn_read_vin.clicked.connect(self.on_read_vin_clicked)
        conn_layout.addWidget(self.btn_read_vin)
        # Área de decodificación VIN
        self.vin_decoded_label = QLabel("")
        self.vin_decoded_label.setWordWrap(True)
        self.vin_decoded_label.setStyleSheet("background: #f8f8f8; border: 1px solid #ccc; padding: 6px; margin-top: 6px;")
        conn_layout.addWidget(self.vin_decoded_label)
        # Botones
        btns_layout = QHBoxLayout()
        self.btn_reconnect = QPushButton("Reconectar")
        self.btn_reconnect.clicked.connect(self.reconnect)
        btns_layout.addWidget(self.btn_reconnect)
        self.btn_disconnect = QPushButton("Desconectar")
        self.btn_disconnect.clicked.connect(self.disconnect_device)
        btns_layout.addWidget(self.btn_disconnect)
        conn_layout.addLayout(btns_layout)
        # Log de conexión
        self.conn_log = QLabel("Log de conexión:")
        self.conn_log.setStyleSheet("font-weight: bold; margin-top: 10px;")
        conn_layout.addWidget(self.conn_log)
        self.conn_log_area = QLabel()
        self.conn_log_area.setWordWrap(True)
        self.conn_log_area.setStyleSheet("background: #f0f0f0; border: 1px solid #ccc; padding: 6px;")
        conn_layout.addWidget(self.conn_log_area)
        self.tabs.addTab(self.conn_tab, "Conexión")
        # --- Pestaña de selección de PIDs ---
        self.select_tab = QWidget()
        select_layout = QVBoxLayout(self.select_tab)
        self.filter_box = QLineEdit()
        self.filter_box.setPlaceholderText("Filtrar por nombre o PID...")
        self.filter_box.textChanged.connect(self.apply_filter)
        select_layout.addWidget(self.filter_box)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)
        select_layout.addWidget(self.scroll_area)
        self.tabs.addTab(self.select_tab, "Seleccionar PIDs")
        # --- Pestaña de datos en vivo ---
        self.data_tab = QWidget()
        data_layout = QVBoxLayout(self.data_tab)
        self.info_label = QLabel("Datos OBD-II en tiempo real:")
        data_layout.addWidget(self.info_label)
        self.data_area = QScrollArea()
        self.data_area.setWidgetResizable(True)
        self.data_content = QWidget()
        self.data_layout = QVBoxLayout()
        self.data_content.setLayout(self.data_layout)
        self.data_area.setWidget(self.data_content)
        data_layout.addWidget(self.data_area)
        self.tabs.addTab(self.data_tab, "Datos en Vivo")
        # --- Pestaña de gauges ---
        self.gauges_tab = QWidget()
        gauges_layout = QVBoxLayout(self.gauges_tab)
        self.gauges_area = QScrollArea()
        self.gauges_area.setWidgetResizable(True)
        self.gauges_content = QWidget()
        self.gauges_layout = QHBoxLayout()
        self.gauges_content.setLayout(self.gauges_layout)
        self.gauges_area.setWidget(self.gauges_content)
        gauges_layout.addWidget(self.gauges_area)
        self.tabs.addTab(self.gauges_tab, "Gauges")
        # --- Pestaña LOG para Tuning ---
        self.log_tab = QWidget()
        log_layout = QVBoxLayout(self.log_tab)
        log_label = QLabel("<b>LOG para Tuning (Stage AMS)</b><br>\nSigue el flujo guiado para registrar un log óptimo para reprogramación y análisis.")
        log_label.setWordWrap(True)
        log_layout.addWidget(log_label)
        # Selector de modo de conducción
        self.drive_mode_box = QComboBox()
        self.drive_mode_box.addItems(["Urbano", "Cruise", "Pull WOT", "Pendientes"])
        self.drive_mode_box.setCurrentIndex(0)
        log_layout.addWidget(QLabel("Modo de conducción actual:"))
        log_layout.addWidget(self.drive_mode_box)
        # Botones de logging
        btns_layout = QHBoxLayout()
        self.btn_start_log = QPushButton("Start Log")
        self.btn_stop_log = QPushButton("Stop Log")
        self.btn_export_csv = QPushButton("Export CSV")
        btns_layout.addWidget(self.btn_start_log)
        btns_layout.addWidget(self.btn_stop_log)
        btns_layout.addWidget(self.btn_export_csv)
        log_layout.addLayout(btns_layout)
        # Estado de logging
        self.log_status_label = QLabel("Estado: No logging")
        log_layout.addWidget(self.log_status_label)
        self.tabs.addTab(self.log_tab, "LOG para Tuning")
        # Backend de logging
        import importlib.util
        import pathlib
        # Buscar data_logger.py en la raíz del proyecto
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
        data_logger_path = os.path.join(project_root, 'data_logger.py')
        spec = importlib.util.spec_from_file_location('data_logger', data_logger_path)
        if spec and spec.loader:
            data_logger_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(data_logger_mod)
            DataLogger = data_logger_mod.DataLogger
        else:
            raise ImportError('No se pudo cargar data_logger.py')
        self.data_logger = DataLogger()
        self.is_logging = False
        self.btn_start_log.clicked.connect(self.start_log)
        self.btn_stop_log.clicked.connect(self.stop_log)
        self.btn_export_csv.clicked.connect(self.export_log_csv)
        self.drive_mode_box.currentIndexChanged.connect(self.on_drive_mode_changed)
        self.current_drive_mode = self.drive_mode_box.currentText()
        # Diagnóstico
        self.dtc_tab = QWidget()
        dtc_layout = QVBoxLayout(self.dtc_tab)
        self.btn_read_dtcs = QPushButton("Leer códigos de falla")
        self.btn_read_dtcs.clicked.connect(self.read_dtcs)
        dtc_layout.addWidget(self.btn_read_dtcs)
        self.btn_clear_dtcs = QPushButton("Borrar códigos de falla")
        self.btn_clear_dtcs.clicked.connect(self.clear_dtcs)
        dtc_layout.addWidget(self.btn_clear_dtcs)
        self.mil_status_label = QLabel("Estado MIL: ...")
        dtc_layout.addWidget(self.mil_status_label)
        self.dtc_list_label = QLabel("Códigos de falla:")
        dtc_layout.addWidget(self.dtc_list_label)
        self.tabs.addTab(self.dtc_tab, "Diagnóstico")
        # Botón cerrar
        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.close)
        main_layout.addWidget(self.btn_close)
        # --- NUEVO: Pestaña de selección de Gauges ---
        self.gauge_select_tab = QWidget()
        gauge_select_layout = QVBoxLayout(self.gauge_select_tab)
        self.gauge_select_box = QGroupBox("Selecciona los PIDs a mostrar como gauges")
        self.gauge_select_layout = QVBoxLayout(self.gauge_select_box)
        self.gauge_checkboxes = {}
        # Usar todos los PIDs disponibles
        all_pids = self.pid_manager.list_all_pids() if self.pid_manager else [normalizar_pid(pid) for pid in PIDS.keys()]
        for pid in all_pids:
            info = self.pid_manager.get_pid_info(pid) if self.pid_manager else PIDS.get(pid, {})
            name = info.get("desc", pid) if info else pid
            cb = QCheckBox(f"{name} ({pid})")
            cb.setChecked(False)
            self.gauge_checkboxes[pid] = cb
            self.gauge_select_layout.addWidget(cb)
        self.gauge_select_box.setLayout(self.gauge_select_layout)
        gauge_select_layout.addWidget(self.gauge_select_box)
        # Botón de confirmación
        self.btn_confirm_gauges = QPushButton("Confirmar selección de gauges")
        self.btn_confirm_gauges.clicked.connect(self.on_confirm_gauges)
        gauge_select_layout.addWidget(self.btn_confirm_gauges)
        self.tabs.addTab(self.gauge_select_tab, "Selección de Gauges")
        # --- Pestaña de gauges (vacía al inicio) ---
        self.gauges_tab = QWidget()
        self.gauges_layout = QHBoxLayout(self.gauges_tab)
        self.gauges_area = QScrollArea()
        self.gauges_area.setWidgetResizable(True)
        self.gauges_content = QWidget()
        self.gauges_content_layout = QHBoxLayout(self.gauges_content)
        self.gauges_area.setWidget(self.gauges_content)
        self.gauges_layout.addWidget(self.gauges_area)
        self.tabs.addTab(self.gauges_tab, "Gauges")
        # Indicador visual de conexión
        self.connection_indicator = QLabel()
        self.connection_indicator.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.connection_indicator.setStyleSheet("font-weight: bold; font-size: 15px; padding: 4px;")
        main_layout.insertWidget(0, self.connection_indicator)
        # Escaneo automático de PIDs soportados
        self.supported_pids = None
        self.handle_vehicle_identification()
        self.populate_pid_labels()
        self.tabs.currentChanged.connect(self.on_tab_changed)
        # Panel CAN Bus
        self.can_viewer = CanSignalViewer()
        self.btn_activate_can = QPushButton("Activar Simulación CAN")
        self.btn_activate_can.clicked.connect(self.on_activate_can)
        main_layout.addWidget(self.btn_activate_can)
        main_layout.addWidget(self.can_viewer)

    def on_id_mode_changed(self, idx):
        self.vehicle_id_mode = idx
        self.handle_vehicle_identification()

    def handle_vehicle_identification(self):
        """Gestiona el flujo según el modo de identificación seleccionado."""
        if self.vehicle_id_mode == 0:
            self.read_vin()
            self.scan_supported_pids()
        elif self.vehicle_id_mode == 1:
            self.select_manual_vehicle()
            self.scan_supported_pids()
        else:
            self.scan_generic_pids()
        self.populate_pid_labels()

    def populate_pid_labels(self):
        # Limpia el layout de selección
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget:
                widget.setParent(None)
        self.checkboxes.clear()
        # Agrupar por nombre (primera palabra del nombre)
        grupos = {}
        # Usar solo los PIDs soportados si están disponibles
        if hasattr(self, 'supported_pids') and self.supported_pids:
            pids = self.supported_pids
        else:
            pids = self.pid_manager.list_all_pids() if self.pid_manager else [normalizar_pid(pid) for pid in PIDS.keys()]
        for pid in pids:
            info = self.pid_manager.get_pid_info(pid) if self.pid_manager else PIDS.get(pid, {})
            group = "Otros"
            if info and info.get("desc"):
                group = info["desc"].split()[0]
            if group not in grupos:
                grupos[group] = []
            grupos[group].append((pid, info))
        # Filtro
        filtro = self.filter_box.text().lower() if hasattr(self, 'filter_box') else ""
        for group, items in sorted(grupos.items()):
            group_box = QGroupBox(group)
            form = QFormLayout()
            for pid, info in items:
                name = pid
                if info:
                    name = info.get("desc", pid)
                if filtro and filtro not in name.lower() and filtro not in pid.lower():
                    continue
                cb = QCheckBox(f"{name} ({pid})")
                cb.setChecked(pid in self.selected_pids)
                cb.stateChanged.connect(functools.partial(self.on_pid_checkbox, pid))
                self.checkboxes[pid] = cb
                form.addRow(cb)
            if form.rowCount() > 0:
                group_box.setLayout(form)
                self.scroll_layout.addWidget(group_box)
        # Actualizar la vista de datos
        self.populate_data_labels()

    def populate_data_labels(self):
        # Limpia el layout de datos
        for i in reversed(range(self.data_layout.count())):
            item = self.data_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget:
                widget.setParent(None)
        self.labels.clear()
        # Solo mostrar los seleccionados
        for pid in (self.selected_pids if self.selected_pids else ([normalizar_pid(pid) for pid in PIDS.keys()] if not self.pid_manager else self.pid_manager.list_all_pids())):
            info = self.pid_manager.get_pid_info(pid) if self.pid_manager else PIDS.get(pid, {})
            name = pid
            if info:
                name = info.get("desc", pid)
            label = QLabel(f"{name} ({pid}): ...")
            self.labels[pid] = label
            self.data_layout.addWidget(label)
        # Gauges
        for i in reversed(range(self.gauges_layout.count())):
            item = self.gauges_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget:
                widget.setParent(None)
        self.gauge_widgets.clear()
        for idx, pid in enumerate(self.selected_pids if self.selected_pids else ([normalizar_pid(pid) for pid in PIDS.keys()] if not self.pid_manager else self.pid_manager.list_all_pids())):
            info = self.pid_manager.get_pid_info(pid) if self.pid_manager else PIDS.get(pid, {})
            name = pid
            min_v = 0
            max_v = 100
            unit = ""
            if info:
                name = info.get("desc", pid)
                min_v = info.get("min", 0)
                max_v = info.get("max", 100)
                unit = info.get("unidades", "")
            # Gauge moderno tipo auto
            import sys
            import os
            gauge_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../src/ui/widgets/gauge.py'))
            import importlib.util
            spec = importlib.util.spec_from_file_location('GaugeWidget', gauge_path)
            if spec and spec.loader:
                gauge_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(gauge_mod)
                GaugeWidget = gauge_mod.GaugeWidget
            else:
                raise ImportError('No se pudo cargar GaugeWidget')
            gauge = GaugeWidget(min_value=min_v, max_value=max_v, units=unit, color=get_gauge_color(idx))
            self.gauge_widgets[pid] = gauge
            # --- NUEVO: Añadir etiqueta descriptiva arriba del gauge ---
            gauge_container = QWidget()
            vlayout = QVBoxLayout()
            vlayout.setContentsMargins(0, 0, 0, 0)
            vlayout.setSpacing(2)
            label_widget = QLabel(name)
            label_widget.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            # Cambiar a color negro, negrita, tamaño grande, sin sombra
            label_widget.setStyleSheet("""
                color: #111;
                font-weight: bold;
                font-size: 18px;
                padding: 2px 0 6px 0;
            """)
            vlayout.addWidget(label_widget)
            vlayout.addWidget(gauge)
            gauge_container.setLayout(vlayout)
            self.gauges_layout.addWidget(gauge_container)

    def on_pid_checkbox(self, pid, state):
        if state:
            self.selected_pids.add(pid)
        else:
            self.selected_pids.discard(pid)
        self.populate_pid_labels()

    def on_gauge_checkbox(self, pid, state):
        if state:
            self.selected_pids.add(pid)
        else:
            self.selected_pids.discard(pid)
        self.populate_data_labels()

    def apply_filter(self):
        self.populate_pid_labels()

    def update_conn_params(self):
        if self.elm327:
            ip = getattr(self.elm327, 'ip', 'N/A')
            port = getattr(self.elm327, 'port', 'N/A')
            modo = getattr(self.elm327, 'mode', 'N/A')
            self.conn_params.setText(f"IP: {ip}   Puerto: {port}   Modo: {modo}")
        else:
            self.conn_params.setText("Sin información de conexión")

    def read_vin(self):
        """Lee el VIN usando el modo 09 PID 02 y decodifica la info si es posible."""
        if not self.elm327 or not hasattr(self.elm327, 'query'):
            self.vin_label.setText("VIN: No disponible (sin conexión)")
            return
        try:
            respuesta = self.elm327.query('09 02')
            if not respuesta:
                self.vin_label.setText("VIN: No disponible (sin respuesta)")
                return
            partes = respuesta.strip().split()
            vin_bytes = []
            i = 0
            while i < len(partes):
                if len(partes) - i >= 4 and partes[i] == '49' and partes[i+1] == '02':
                    vin_bytes.extend(partes[i+3:i+7])
                    i += 7
                else:
                    i += 1
            if not vin_bytes:
                self.vin_label.setText("VIN: No encontrado")
                return
            vin = ''.join([chr(int(b, 16)) for b in vin_bytes if len(b) == 2])
            vin = vin.strip()
            self.vehicle_info['vin'] = vin
            if vin:
                self.vin_label.setText(f"VIN: {vin}")
            else:
                self.vin_label.setText("VIN: No encontrado")
        except Exception:
            self.vin_label.setText("VIN: Error de lectura")

    def select_manual_vehicle(self):
        """Muestra diálogo para selección manual de marca/modelo/año/motor."""
        # Ejemplo simple: puedes expandir con más lógica y combos
        marca, ok = QInputDialog.getText(self, "Marca", "Marca del vehículo:")
        if not ok:
            return
        modelo, ok = QInputDialog.getText(self, "Modelo", "Modelo del vehículo:")
        if not ok:
            return
        anio, ok = QInputDialog.getText(self, "Año", "Año del vehículo:")
        if not ok:
            return
        motor, ok = QInputDialog.getText(self, "Motor", "Motor:")
        if not ok:
            return
        self.vehicle_info = {'marca': marca, 'modelo': modelo, 'anio': anio, 'motor': motor}
        self.vin_label.setText(f"Manual: {marca} {modelo} {anio} {motor}")

    def scan_generic_pids(self):
        """Carga solo PIDs estándar (sin identificación de vehículo)."""
        self.supported_pids = [pid for pid in PIDS.keys() if int(pid, 16) <= 0x20]
        self.vin_label.setText("Modo genérico: solo PIDs estándar")

    def read_dtcs(self):
        """Lee códigos de falla (DTCs) usando modo 03 y muestra descripciones."""
        if not self.elm327 or not hasattr(self.elm327, 'query'):
            QMessageBox.warning(self, "Error", "No hay conexión con ELM327")
            return
        try:
            respuesta = self.elm327.query('03')
            if not respuesta:
                self.dtc_list_label.setText("Códigos de falla: No disponible")
                return
            dtcs = self.parse_dtcs(respuesta)
            if dtcs:
                self.dtc_list_label.setText("Códigos de falla: " + ', '.join(dtcs))
            else:
                self.dtc_list_label.setText("Códigos de falla: Ninguno")
            self.read_mil_status()
        except Exception:
            self.dtc_list_label.setText("Códigos de falla: Error de lectura")

    def clear_dtcs(self):
        """Borra códigos de falla usando modo 04."""
        if not self.elm327 or not hasattr(self.elm327, 'query'):
            QMessageBox.warning(self, "Error", "No hay conexión con ELM327")
            return
        try:
            self.elm327.query('04')
            self.dtc_list_label.setText("Códigos de falla: Borrados")
            self.read_mil_status()
        except Exception:
            self.dtc_list_label.setText("Códigos de falla: Error al borrar")

    def read_mil_status(self):
        """Lee el estado de la MIL (Check Engine) usando PID 01 01."""
        if not self.elm327 or not hasattr(self.elm327, 'query'):
            self.mil_status_label.setText("Estado MIL: No disponible")
            return
        try:
            respuesta = self.elm327.query('01 01')
            if not respuesta:
                self.mil_status_label.setText("Estado MIL: No disponible")
                return
            partes = respuesta.strip().split()
            if len(partes) >= 3:
                byteA = int(partes[2], 16)
                mil_on = (byteA & 0x80) != 0
                self.mil_status_label.setText(f"Estado MIL: {'ENCENDIDA' if mil_on else 'APAGADA'}")
            else:
                self.mil_status_label.setText("Estado MIL: Respuesta inválida")
        except Exception:
            self.mil_status_label.setText("Estado MIL: Error de lectura")

    def parse_dtcs(self, respuesta):
        """Decodifica la respuesta de modo 03 a una lista de DTCs."""
        # Implementación básica, puedes mejorarla según el formato de tu ELM327
        partes = respuesta.strip().split()
        dtcs = []
        if len(partes) > 2:
            bytes_hex = partes[2:]
            for i in range(0, len(bytes_hex), 2):
                if i+1 < len(bytes_hex):
                    code = bytes_hex[i] + bytes_hex[i+1]
                    if code != '0000':
                        dtcs.append(code)
        return dtcs

    def run_diagnostic_tests(self):
        """Prueba automática de diagnóstico: conexión, identificación, DTCs y PIDs."""
        results = []
        # Test conexión
        if self.elm327 and hasattr(self.elm327, 'query'):
            results.append("Conexión ELM327: OK")
        else:
            results.append("Conexión ELM327: ERROR")
        # Test identificación
        if self.vehicle_id_mode == 0 and self.vehicle_info.get('vin'):
            results.append(f"Identificación VIN: {self.vehicle_info['vin']}")
        elif self.vehicle_id_mode == 1 and self.vehicle_info.get('marca'):
            results.append("Identificación manual: OK")
        elif self.vehicle_id_mode == 2:
            results.append("Modo genérico: OK")
        else:
            results.append("Identificación: ERROR")
        # Test DTCs
        try:
            self.read_dtcs()
            results.append("Lectura DTCs: OK")
        except Exception:
            results.append("Lectura DTCs: ERROR")
        # Test PIDs
        if self.supported_pids:
            results.append(f"Escaneo PIDs: {len(self.supported_pids)} encontrados")
        else:
            results.append("Escaneo PIDs: ERROR")
        QMessageBox.information(self, "Resultados de diagnóstico", '\n'.join(results))

    def update_connection_indicator(self):
        """Actualiza el indicador visual de conexión."""
        if self.elm327 and getattr(self.elm327, 'connected', False):
            self.connection_indicator.setText("🟢 Conectado")
            self.connection_indicator.setStyleSheet("color: #0a0; font-weight: bold; font-size: 15px; padding: 4px;")
        else:
            self.connection_indicator.setText("🔴 Desconectado")
            self.connection_indicator.setStyleSheet("color: #b00; font-weight: bold; font-size: 15px; padding: 4px;")

    def update_data(self, data=None):
        if data is None:
            data = self.get_data_fn()
        for pid, value in data.items():
            name = pid
            val = 0
            info = self.pid_manager.get_pid_info(pid) if self.pid_manager else PIDS.get(pid, {})
            if info:
                name = info.get("desc", pid)
            # Validación robusta de tipo para evitar errores de comparación str/int
            try:
                # Si value es un dict (como en CAN simulado), extraer 'value'
                if isinstance(value, dict) and 'value' in value:
                    val = value['value']
                else:
                    val = value
                # Forzar a float si es posible, si no, 0
                if isinstance(val, str):
                    val = float(val.split()[0]) if val.strip() else 0
                elif not isinstance(val, (int, float)):
                    val = 0
            except Exception:
                val = 0
            if pid in self.labels:
                self.labels[pid].setText(f"{name} ({pid}): {value}")
            if pid in self.gauge_widgets:
                self.gauge_widgets[pid].set_value(val)
        # Indicador de conexión
        self.update_connection_indicator()
        # Advertencia si RPM está deshabilitado
        if '010C' in self.checkboxes and not self.checkboxes['010C'].isEnabled():
            if hasattr(self, 'labels') and '010C' in self.labels:
                self.labels['010C'].setStyleSheet("color: #b00; font-weight: bold; background: #fff3cd;")
                self.labels['010C'].setText(self.labels['010C'].text() + " [RPM deshabilitado]")
        # Actualizar estado de conexión y parámetros
        if hasattr(self, 'conn_status'):
            if self.elm327 and getattr(self.elm327, 'connected', False):
                self.conn_status.setText("Estado: Conectado")
            else:
                self.conn_status.setText("Estado: Desconectado")
        if hasattr(self, 'conn_params'):
            self.update_conn_params()
        # Actualizar log de conexión
        if hasattr(self, 'conn_log_area'):
            log = getattr(self.elm327, 'logger', None)
            if log and hasattr(log, 'handlers') and log.handlers:
                try:
                    handler = log.handlers[0]
                    if hasattr(handler, 'stream') and hasattr(handler.stream, 'getvalue'):
                        self.conn_log_area.setText(handler.stream.getvalue())
                except Exception:
                    pass
        # Logging si está activo
        if hasattr(self, 'is_logging') and self.is_logging:
            # Añadir el modo de conducción actual a cada registro
            data_with_mode = data.copy()
            data_with_mode['drive_mode'] = {'name': 'Modo de conducción', 'value': self.current_drive_mode, 'unit': ''}
            self.data_logger.log_data(data_with_mode)

    def disable_pid(self, pid):
        if pid in self.checkboxes:
            self.checkboxes[pid].setChecked(False)
            self.checkboxes[pid].setEnabled(False)
        if pid in self.labels:
            self.labels[pid].setStyleSheet("color: #b00; font-weight: bold; background: #fff3cd;")
            self.labels[pid].setText(self.labels[pid].text() + " [Deshabilitado]")
        if pid == '010C':
            self.labels[pid].setText(self.labels[pid].text() + " [PID RPM crítico]")
        if pid in self.gauge_widgets:
            # Cambiar color del gauge a gris y marcarlo como inválido
            self.gauge_widgets[pid].setStyleSheet("background: #eee; border: 2px solid #b00;")
            self.gauge_widgets[pid].set_value("NO DATA")  # Mostrará '---' y atenuado

    def reconnect(self):
        if self.elm327:
            self.elm327.close()
            self.elm327.connect()
        self.read_vin()
        self.update_data()

    def disconnect_device(self):
        if self.elm327:
            self.elm327.close()
        self.update_data()

    def on_read_vin_clicked(self):
        import importlib.util
        import os
        vin_decoder_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../vin_decoder.py'))
        spec = importlib.util.spec_from_file_location('vin_decoder', vin_decoder_path)
        if spec and spec.loader:
            vin_decoder_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(vin_decoder_mod)
            decode_vin = vin_decoder_mod.decode_vin
        else:
            raise ImportError('No se pudo cargar vin_decoder.py')
        self.read_vin()
        vin = self.vehicle_info.get('vin', None)
        if vin:
            data = decode_vin(vin)
            if data['valid']:
                msg = f"<b>VIN:</b> {vin}<br>"
                msg += f"<b>País:</b> {data['country']}<br>"
                msg += f"<b>Fabricante:</b> {data['manufacturer']}<br>"
                msg += f"<b>Tipo:</b> {data['vehicle_type']}<br>"
                msg += f"<b>Año:</b> {data['year']}<br>"
                msg += f"<b>Planta:</b> {data['plant']}<br>"
                msg += f"<b>Serie:</b> {data['serial']}"
                self.vin_decoded_label.setText(msg)
                QMessageBox.information(self, "VIN leído", f"VIN detectado: {vin}\n\nDecodificado:\nPaís: {data['country']}\nFabricante: {data['manufacturer']}\nAño: {data['year']}")
            else:
                self.vin_decoded_label.setText(f"<b>VIN inválido:</b> {data['error']}")
                QMessageBox.warning(self, "VIN no válido", data['error'])
        else:
            self.vin_decoded_label.setText("")
            QMessageBox.warning(self, "VIN no detectado", "No se pudo leer el VIN del vehículo.")

    def show_logging_tab_popup(self):
        msg = (
            "Estás en la pestaña <b>LOG para Tuning</b>. Sigue el flujo guiado para generar un log para Stage AMS:<br><br>"
            "1. Selecciona un modo de conducción: Urbano, Cruise, Pull WOT o Pendientes.<br>"
            "2. Presiona <b>Start Log</b> para iniciar.<br>"
            "3. Se leerán automáticamente estos PIDs cada 200‑500 ms:<br>"
            "<i>timestamp, drive_mode, rpm, speed, maf, engine_load, coolant_temp, intake_temp, map, tps, ignition_advance, lambda, stft, ltft, fuel_rate, egr (si aplica), distance</i>.<br>"
            "4. Conduce según el modo seleccionado:<br>"
            "• <b>Urbano</b>: 15 min de tráfico mixto<br>"
            "• <b>Cruise</b>: 10 min a 100‑120 km/h constantes<br>"
            "• <b>Pull WOT</b>: 3‑5 aceleraciones de 2 500 rpm a redline<br>"
            "• <b>Pendientes</b>: 5‑10 min en subidas y bajadas continuas<br>"
            "5. Puedes cambiar el modo durante la grabación; <code>drive_mode</code> se registra en cada muestra.<br>"
            "6. Al finalizar, pulsa <b>Stop Log</b>. Si no se cumple el mínimo, se mostrará un aviso.<br>"
            "7. Pulsa <b>Export CSV</b> para obtener un archivo completo con <code>drive_mode</code>.<br>"
            "8. Usa este log con ChatGPT para generar mejoras de mapa Stage AMS."
        )
        QMessageBox.information(self, "🎯 Instrucciones – LOG para Tuning (Stage AMS)", msg)

    def show_logging_wizard(self):
        # Mostrar los pasos uno a uno, esperando confirmación del usuario en cada paso
        pasos = [
            "👉 Paso 1/8 — Selecciona el modo de conducción antes de iniciar el log.",
            "👉 Paso 2/8 — Pulsa <b>Start Log</b> para comenzar la grabación.",
            "👉 Paso 3/8 — Espera confirmación de que el log está activo.",
            "👉 Paso 4/8 — Conduce según el modo:\n   • Urbano → 15 min tráfico mixto\n   • Cruise → 10 min velocidad constante\n   • Pull WOT → 3‑5 aceleraciones de 2 500 rpm a redline\n   • Pendientes → 5‑10 min subidas y bajadas",
            "👉 Paso 5/8 — Puedes cambiar el modo durante la grabación; <code>drive_mode</code> se actualiza automáticamente.",
            "👉 Paso 6/8 — Cuando termines el escenario, pulsa <b>Stop Log</b>.",
            "👉 Paso 7/8 — Validación automática:\n   • Urbano ≥15 min\n   • Cruise ≥10 min\n   • Pull WOT → 3‑5 tirones\n   • Pendientes ≥5 min\n   Si no se cumplen, mostrar aviso.",
            "👉 Paso 8/8 — Log completo. Pulsa <b>Export CSV</b> para guardar todos los datos y <code>drive_mode</code>. ¡Listo para tuning AMS!"
        ]
        for paso in pasos:
            QMessageBox.information(self, "LOG para Tuning – Asistente", paso)
            # Esperar a que el usuario cierre el mensaje antes de mostrar el siguiente

    def on_tab_changed(self, idx):
        if hasattr(self.tabs, 'tabText') and self.tabs.tabText(idx) == "LOG para Tuning":
            if not hasattr(self, '_log_tab_popup_shown'):
                self.show_logging_tab_popup()
                self._log_tab_popup_shown = True
                self.show_logging_wizard()

    def start_log(self):
        if not self.is_logging:
            self.data_logger.start_logging()
            self.is_logging = True
            self.log_status_label.setText(f"Estado: Logging activo ({self.current_drive_mode})")
        else:
            QMessageBox.information(self, "Logging", "Ya está en curso una sesión de logging.")

    def stop_log(self):
        if self.is_logging:
            self.is_logging = False
            self.log_status_label.setText("Estado: Logging detenido")
            self.data_logger.close()
        else:
            QMessageBox.information(self, "Logging", "No hay logging activo.")

    def export_log_csv(self):
        status = self.data_logger.get_status()
        if not status.get('active') or not status.get('file') or not isinstance(status.get('file'), str):
            QMessageBox.warning(self, "Exportar CSV", "No hay log activo para exportar.")
            return
        from PyQt6.QtWidgets import QFileDialog
        fname, _ = QFileDialog.getSaveFileName(self, "Guardar log como", "obd_log.csv", "CSV (*.csv)")
        if not fname:
            return
        try:
            import shutil
            shutil.copyfile(str(status['file']), fname)
            QMessageBox.information(self, "Exportar CSV", f"Log exportado a {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

    def on_drive_mode_changed(self, idx):
        self.current_drive_mode = self.drive_mode_box.currentText()
        if self.is_logging:
            # Registrar cambio de modo en el log
            self.data_logger.log_data({
                'drive_mode': {
                    'name': 'Modo de conducción',
                    'value': self.current_drive_mode,
                    'unit': ''
                }
            })

    def update_can_data(self, data_dict):
        self.can_viewer.update_can_data(data_dict)

    def on_activate_can(self):
        # Carga dinámica de módulos con manejo robusto de errores
        def load_mod(name):
            try:
                path = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../../{name}.py'))
                if not os.path.isfile(path):
                    QMessageBox.critical(self, "Error de módulo", f"No se encontró el archivo {name}.py en {path}")
                    return None
                spec = importlib.util.spec_from_file_location(name, path)
                if not spec or not spec.loader:
                    QMessageBox.critical(self, "Error de módulo", f"No se pudo crear el spec para {name}.py")
                    return None
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
            except Exception as e:
                QMessageBox.critical(self, "Error de módulo", f"Error cargando {name}.py:\n{e}")
                return None
        dbc_loader = load_mod('dbc_loader')
        simulator_can = load_mod('simulator_can')
        can_logger = load_mod('can_logger')
        if not (dbc_loader and simulator_can and can_logger):
            return
        try:
            dbc_dir = dbc_loader.ensure_dbc_folder()
            dbc_files = [f for f in os.listdir(dbc_dir) if f.endswith('.dbc')]
            if not dbc_files:
                QMessageBox.warning(self, "Simulación CAN", "No hay archivos DBC disponibles.")
                return
            dbc_path = os.path.join(dbc_dir, dbc_files[0])
            try:
                db = dbc_loader.load_dbc(dbc_path)
            except Exception as e:
                QMessageBox.critical(self, "Simulación CAN", f"Error cargando DBC:\n{e}")
                return
            if not db.messages:
                QMessageBox.warning(self, "Simulación CAN", "El archivo DBC no contiene mensajes CAN válidos.")
                return
            msg = db.messages[0]
            def on_can_data(data):
                self.update_can_data(data)
                try:
                    can_logger.log_can_to_csv(os.path.join(os.path.dirname(__file__), '../../logs'), msg.name, data)
                except Exception as e:
                    print(f"Error al registrar CAN: {e}")
            import threading
            if hasattr(self, '_can_stop_event') and self._can_stop_event:
                self._can_stop_event.set()
            self._can_stop_event = threading.Event()
            try:
                simulator_can.simulate_can_messages(db, msg.name, on_can_data, interval_ms=500, stop_event=self._can_stop_event)
            except Exception as e:
                QMessageBox.critical(self, "Simulación CAN", f"Error al iniciar simulación:\n{e}")
                return
            QMessageBox.information(self, "Simulación CAN", f"Simulación de '{msg.name}' activada desde {dbc_files[0]}")
        except Exception as e:
            QMessageBox.critical(self, "Simulación CAN", f"Error inesperado:\n{e}")
