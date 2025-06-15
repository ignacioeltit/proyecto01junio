"""Graphical user interface."""

from __future__ import annotations

from typing import List

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTabWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QCheckBox,
    QLineEdit,
    QSpinBox,
)
from PySide6.QtCore import Qt

from ..core.pid_manager import PIDManager
from ..core.dtc_manager import DTCManager
from ..core.vin_reader import VINReader
from ..core.obd_interface import OBDInterface
from ..core.config import Config
from ..core.logger import setup_logger
from .gauges_widget import Gauge
from .realtime_plot import RealTimePlot


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.setWindowTitle("OBD-II Scanner")
        self.config = config
        self.interface = OBDInterface(config.obd_url, config.simulator, config.debug)
        self.pid_manager = PIDManager(self.interface.connection, self.interface.simulator, self.interface.logger)
        self.dtc_manager = DTCManager(self.interface.connection, self.interface.simulator, self.interface.logger)
        self.vin_reader = VINReader(self.interface.connection, self.interface.simulator, self.interface.logger)
        self._build_ui()

    # UI Construction -----------------------------------------------------
    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tab_home = QWidget()
        self.tab_diag = QWidget()
        self.tab_pids = QWidget()
        self.tab_gauges = QWidget()
        self.tab_graph = QWidget()
        self.tab_logs = QWidget()
        self.tab_config = QWidget()

        self.tabs.addTab(self.tab_home, "Inicio")
        self.tabs.addTab(self.tab_diag, "Diagnóstico")
        self.tabs.addTab(self.tab_pids, "PIDs en Vivo")
        self.tabs.addTab(self.tab_gauges, "Gauges")
        self.tabs.addTab(self.tab_graph, "Gráficos")
        self.tabs.addTab(self.tab_logs, "Logs")
        self.tabs.addTab(self.tab_config, "Configuración")

        self._init_home()
        self._init_diag()
        self._init_pids()
        self._init_gauges()
        self._init_graph()
        self._init_logs()
        self._init_config()

    # Home tab ------------------------------------------------------------
    def _init_home(self) -> None:
        layout = QVBoxLayout()
        self.status_label = QLabel("Desconectado")
        self.protocol_label = QLabel("-")
        self.vin_label = QLabel("-")
        self.btn_connect = QPushButton("Conectar")
        self.btn_connect.clicked.connect(self._toggle_connection)
        layout.addWidget(self.status_label)
        layout.addWidget(self.protocol_label)
        layout.addWidget(self.vin_label)
        layout.addWidget(self.btn_connect)
        self.tab_home.setLayout(layout)

    def _toggle_connection(self) -> None:
        if self.interface.is_connected():
            self.interface.close()
            self.status_label.setText("Desconectado")
            self.btn_connect.setText("Conectar")
            return
        self.interface.connect()
        if self.interface.is_connected():
            self.status_label.setText("Conectado")
            self.btn_connect.setText("Desconectar")
            vin = self.vin_reader.read()
            if vin:
                self.vin_label.setText(self.vin_reader.decode(vin))
            if not self.interface.use_simulator:
                self.protocol_label.setText(str(self.interface.connection.protocol_name()))
        else:
            self.status_label.setText("Simulador")
            self.btn_connect.setText("Desconectar")

    # Diagnostics tab -----------------------------------------------------
    def _init_diag(self) -> None:
        layout = QVBoxLayout()
        self.btn_read_dtc = QPushButton("Leer DTCs")
        self.btn_clear_dtc = QPushButton("Borrar DTCs")
        self.dtc_list = QListWidget()
        self.btn_read_dtc.clicked.connect(self._read_dtcs)
        self.btn_clear_dtc.clicked.connect(self._clear_dtcs)
        layout.addWidget(self.btn_read_dtc)
        layout.addWidget(self.btn_clear_dtc)
        layout.addWidget(self.dtc_list)
        self.tab_diag.setLayout(layout)

    def _read_dtcs(self) -> None:
        self.dtc_list.clear()
        for dtc in self.dtc_manager.read():
            self.dtc_list.addItem(dtc)

    def _clear_dtcs(self) -> None:
        if self.dtc_manager.clear():
            self.dtc_list.clear()

    # PIDs tab ------------------------------------------------------------
    def _init_pids(self) -> None:
        layout = QVBoxLayout()
        self.pid_list = QListWidget()
        for pid in self.pid_manager.supported_pids():
            item = QListWidgetItem(pid)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.pid_list.addItem(item)
        self.btn_start_pids = QPushButton("Iniciar")
        self.btn_start_pids.clicked.connect(self._start_pids)
        self.values_layout = QVBoxLayout()
        layout.addWidget(self.pid_list)
        layout.addWidget(self.btn_start_pids)
        layout.addLayout(self.values_layout)
        self.tab_pids.setLayout(layout)
        self.stream_handle = None

    def _start_pids(self) -> None:
        selected = []
        for i in range(self.pid_list.count()):
            it = self.pid_list.item(i)
            if it.checkState() == Qt.Checked:
                selected.append(it.text())
        if not selected:
            return
        for i in reversed(range(self.values_layout.count())):
            w = self.values_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        labels = {pid: QLabel(f"{pid}: --") for pid in selected}
        for lbl in labels.values():
            self.values_layout.addWidget(lbl)

        def cb(pid: str, value: str) -> None:
            labels[pid].setText(f"{pid}: {value}")
        self.stream_handle = self.pid_manager.start_stream(selected, cb)

    # Gauges tab ----------------------------------------------------------
    def _init_gauges(self) -> None:
        layout = QHBoxLayout()
        self.gauge_rpm = Gauge("RPM", maximum=8000)
        self.gauge_speed = Gauge("Velocidad", maximum=200)
        layout.addWidget(self.gauge_rpm)
        layout.addWidget(self.gauge_speed)
        self.tab_gauges.setLayout(layout)

    # Graph tab -----------------------------------------------------------
    def _init_graph(self) -> None:
        layout = QVBoxLayout()
        self.graph = RealTimePlot("RPM")
        layout.addWidget(self.graph)
        self.tab_graph.setLayout(layout)

    # Logs tab ------------------------------------------------------------
    def _init_logs(self) -> None:
        layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)
        self.tab_logs.setLayout(layout)
        # simple logging handler
        import logging
        handler = logging.Handler()

        def emit(record):
            self.log_view.append(logging.getLogger().formatter.format(record))

        handler.emit = emit  # type: ignore
        logging.getLogger('scanner').addHandler(handler)

    # Config tab ----------------------------------------------------------
    def _init_config(self) -> None:
        layout = QVBoxLayout()
        self.le_url = QLineEdit(self.config.obd_url)
        self.cb_sim = QCheckBox("Usar simulador")
        self.cb_sim.setChecked(self.config.simulator)
        self.cb_debug = QCheckBox("Modo debug")
        self.cb_debug.setChecked(self.config.debug)
        self.btn_save_cfg = QPushButton("Guardar")
        self.btn_save_cfg.clicked.connect(self._save_config)
        layout.addWidget(QLabel("URL OBD"))
        layout.addWidget(self.le_url)
        layout.addWidget(self.cb_sim)
        layout.addWidget(self.cb_debug)
        layout.addWidget(self.btn_save_cfg)
        self.tab_config.setLayout(layout)

    def _save_config(self) -> None:
        self.config.obd_url = self.le_url.text()
        self.config.simulator = self.cb_sim.isChecked()
        self.config.debug = self.cb_debug.isChecked()
        self.config.save()
        self.interface.logger.info("Configuration saved")

