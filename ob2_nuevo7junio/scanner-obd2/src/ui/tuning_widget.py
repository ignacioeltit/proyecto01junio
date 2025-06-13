# tuning_widget.py
"""
Widget de Tuning para selección y visualización de PIDs críticos en tiempo real.
Permite seleccionar PIDs según vehículo y muestra gauges/gráficos en vivo.
Emite señal tuning_update(session_id, map_version, pid_values_dict).
"""
import json
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout
from PySide6.QtCore import Signal, Qt, QTimer
from ui.widgets.simple_gauge import SpeedometerGaugeWidget
import pyqtgraph as pg

class TuningWidget(QWidget):
    tuning_update = Signal(str, str, dict)  # session_id, map_version, pid_values_dict

    def __init__(self, vehicle_info=None, parent=None):
        super().__init__(parent)
        self.vehicle_info = vehicle_info or {}
        self.pid_defs = self.load_pid_definitions()
        self.selected_pids = []
        self.session_id = ""
        self.map_version = ""
        self.last_pid_values = {}
        self._setup_ui()
        self._setup_timer()

    def load_pid_definitions(self):
        path = os.path.join(os.path.dirname(__file__), '../../data/pid_definitions.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {}

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>PIDs críticos para Tuning</b>"))
        self.pid_list = QListWidget()
        self.pid_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.pid_list)
        self.reload_btn = QPushButton("Recargar PIDs según vehículo")
        self.reload_btn.clicked.connect(self.reload_pids)
        layout.addWidget(self.reload_btn)
        # Visualización en vivo
        self.gauge_layout = QHBoxLayout()
        layout.addLayout(self.gauge_layout)
        self.graph = pg.PlotWidget(title="Tuning Live Data")
        self.graph.showGrid(x=True, y=True)
        layout.addWidget(self.graph)
        self.setLayout(layout)
        self.reload_pids()

    def reload_pids(self):
        self.pid_list.clear()
        make = self.vehicle_info.get('make', 'default')
        model = self.vehicle_info.get('model', 'default')
        # Filtra PIDs críticos por vehículo
        pids = self.pid_defs.get(make, {}).get(model, []) or self.pid_defs.get('default', [])
        for pid in pids:
            item = QListWidgetItem(f"{pid['name']} ({pid['code']})")
            item.setData(Qt.ItemDataRole.UserRole, pid)
            self.pid_list.addItem(item)

    def _setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_live)
        self.timer.start(300)

    def set_session(self, session_id, map_version):
        self.session_id = session_id
        self.map_version = map_version

    def update_pid_values(self, pid_values_dict):
        self.last_pid_values = pid_values_dict

    def _update_live(self):
        # Visualización en gauges y gráfico
        selected_items = self.pid_list.selectedItems()
        if not selected_items:
            return
        # Gauges
        for i in reversed(range(self.gauge_layout.count())):
            widget = self.gauge_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        for item in selected_items:
            pid = item.data(Qt.ItemDataRole.UserRole)
            val = self.last_pid_values.get(pid['name'], 0)
            gauge = SpeedometerGaugeWidget(label=pid['name'], min_value=pid.get('min',0), max_value=pid.get('max',100), units=pid.get('unit',''))
            gauge.set_value(val)
            self.gauge_layout.addWidget(gauge)
        # Gráfico
        self.graph.clear()
        for item in selected_items:
            pid = item.data(Qt.ItemDataRole.UserRole)
            name = pid['name']
            ydata = self.last_pid_values.get(f"history_{name}", [])
            if ydata:
                xdata = list(range(len(ydata)))
                self.graph.plot(xdata, ydata, pen=pg.mkPen(width=2), name=name)
        # Emitir señal
        pid_vals = {item.data(Qt.ItemDataRole.UserRole)['name']: self.last_pid_values.get(item.data(Qt.ItemDataRole.UserRole)['name'], 0) for item in selected_items}
        self.tuning_update.emit(self.session_id, self.map_version, pid_vals)
