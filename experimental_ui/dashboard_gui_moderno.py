"""
Dashboard OBD-II Experimental UI v1
-----------------------------------
Enfoque visual: Moderno, dark mode, gauges tipo dial y digital, layout responsive.
- Inspirado en Material Design y dashboards automotrices.
- Incluye conexión/desconexión, selector de modo, gauges visuales y tabla de eventos.
- Compatible con modo emulador y real.
"""

import sys
import os
import random
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QGridLayout, QComboBox, QTableWidget,
    QTableWidgetItem, QSizePolicy, QFrame
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QColor, QPalette

# Reutilizamos la lógica de conexión y parseo del dashboard base
from dashboard_optimizado_wifi_final import OptimizedELM327Connection, DataLogger

class GaugeWidget(QFrame):
    """Widget visual tipo gauge digital/barra para un PID"""
    def __init__(self, label, unit, min_value=0, max_value=100, color='#00e676'):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"background-color: #222; border-radius: 12px; border: 2px solid {color};")
        layout = QVBoxLayout(self)
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #fff; font-size: 16px; font-weight: bold;")
        self.value = QLabel("--")
        self.value.setStyleSheet(f"color: {color}; font-size: 36px; font-weight: bold;")
        self.unit = QLabel(unit)
        self.unit.setStyleSheet("color: #aaa; font-size: 14px;")
        self.bar = QFrame()
        self.bar.setStyleSheet(f"background: {color}; border-radius: 6px;")
        self.bar.setFixedHeight(8)
        layout.addWidget(self.label)
        layout.addWidget(self.value, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.unit, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.bar)
        self.min_value = min_value
        self.max_value = max_value
        self._last = None
    def set_value(self, val):
        self.value.setText(str(val))
        percent = 0
        try:
            percent = (float(val) - self.min_value) / (self.max_value - self.min_value)
            percent = max(0, min(1, percent))
        except:
            percent = 0
        self.bar.setFixedWidth(int(180 * percent))
        self._last = val

class DashboardExperimentalV1(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚗 OBD-II Dashboard Experimental UI v1")
        self.setMinimumSize(900, 600)
        self.elm327 = OptimizedELM327Connection()
        self.logger = DataLogger()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gauges)
        self.slow_timer = QTimer()
        self.slow_timer.timeout.connect(self.update_table)
        self._setup_palette()
        self._build_ui()
        self._connect_signals()
        self.data_cache = {}
        self.slow_data_cache = {}
        self.mode = 'WIFI'
    def _setup_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#181c20'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('#fff'))
        self.setPalette(palette)
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        # Top bar
        top = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["WiFi", "Emulador"])
        self.connect_btn = QPushButton("🔌 Conectar")
        self.connect_btn.setStyleSheet("background:#00e676; color:#222; font-weight:bold; padding:8px 18px; border-radius:8px;")
        self.disconnect_btn = QPushButton("⏹️ Desconectar")
        self.disconnect_btn.setStyleSheet("background:#ff1744; color:#fff; font-weight:bold; padding:8px 18px; border-radius:8px;")
        self.disconnect_btn.setEnabled(False)
        self.status_lbl = QLabel("🔴 DESCONECTADO")
        self.status_lbl.setStyleSheet("color:#ff1744; font-size:16px; font-weight:bold;")
        top.addWidget(QLabel("Modo:"))
        top.addWidget(self.mode_combo)
        top.addWidget(self.connect_btn)
        top.addWidget(self.disconnect_btn)
        top.addWidget(self.status_lbl)
        top.addStretch()
        main.addLayout(top)
        # Gauges
        gauges = QHBoxLayout()
        self.gauges = {}
        self.gauges['010C'] = GaugeWidget("RPM", "RPM", 0, 8000, '#00bcd4')
        self.gauges['010D'] = GaugeWidget("Velocidad", "km/h", 0, 250, '#ffeb3b')
        self.gauges['0105'] = GaugeWidget("Temp Motor", "°C", -40, 150, '#ff5722')
        self.gauges['0104'] = GaugeWidget("Carga Motor", "%", 0, 100, '#8bc34a')
        self.gauges['0111'] = GaugeWidget("Acelerador", "%", 0, 100, '#e040fb')
        for g in self.gauges.values():
            gauges.addWidget(g)
        main.addLayout(gauges)
        # Tabla de eventos/lecturas
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Hora", "PID", "Nombre", "Valor", "Unidad"])
        self.table.setStyleSheet("background:#222; color:#fff; font-size:13px;")
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main.addWidget(self.table)
    def _connect_signals(self):
        self.connect_btn.clicked.connect(self._connect)
        self.disconnect_btn.clicked.connect(self._disconnect)
    def _connect(self):
        mode = self.mode_combo.currentText()
        self.elm327._mode = 'emulator' if mode == 'Emulador' else 'wifi'
        if self.elm327.connect():
            self.status_lbl.setText("🟢 CONECTADO")
            self.status_lbl.setStyleSheet("color:#00e676; font-size:16px; font-weight:bold;")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.timer.start(200)
            self.slow_timer.start(1000)
        else:
            self.status_lbl.setText("🔴 ERROR")
    def _disconnect(self):
        self.timer.stop()
        self.slow_timer.stop()
        self.elm327.disconnect()
        self.status_lbl.setText("🔴 DESCONECTADO")
        self.status_lbl.setStyleSheet("color:#ff1744; font-size:16px; font-weight:bold;")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
    def update_gauges(self):
        # Solo leer los PIDs rápidos
        for pid in self.gauges:
            info = self.elm327.query_pid(pid)
            if info:
                self.gauges[pid].set_value(info['value'])
                self._log_table(pid, info)
    def update_table(self):
        # Leer PIDs lentos y agregarlos a la tabla
        data = self.elm327.read_slow_data()
        if data:
            for pid, info in data.items():
                self._log_table(pid, info)
    def _log_table(self, pid, info):
        now = datetime.now().strftime("%H:%M:%S")
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(now))
        self.table.setItem(row, 1, QTableWidgetItem(pid))
        self.table.setItem(row, 2, QTableWidgetItem(info['name']))
        self.table.setItem(row, 3, QTableWidgetItem(str(info['value'])))
        self.table.setItem(row, 4, QTableWidgetItem(info['unit']))
        self.table.scrollToBottom()

def main():
    app = QApplication(sys.argv)
    win = DashboardExperimentalV1()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
