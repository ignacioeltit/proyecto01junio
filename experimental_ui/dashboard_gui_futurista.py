"""
Dashboard OBD-II Experimental UI v2
-----------------------------------
Enfoque visual: Futurista, dark mode, gauges tipo dial animados, layout adaptable y panel lateral de eventos.
- Inspirado en interfaces de autos eléctricos y paneles de control avanzados.
- Gauges circulares, animaciones suaves, panel lateral para logs.
- Compatible con modo emulador y real.
"""

import sys
import os
import random
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QGridLayout, QComboBox, QListWidget,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QColor, QPalette, QPainter, QPen

from dashboard_optimizado_wifi_final import OptimizedELM327Connection, DataLogger

class CircularGauge(QWidget):
    """Gauge circular animado para valores numéricos"""
    def __init__(self, label, unit, min_value=0, max_value=100, color='#00e676'):
        super().__init__()
        self.label = label
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.value = 0
        self.color = QColor(color)
        self.setMinimumSize(160, 160)
        self.setMaximumSize(200, 200)
        self._last = None
    def set_value(self, val):
        self.value = float(val)
        self.update()
        self._last = val
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)
        # Fondo
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#222'))
        painter.drawEllipse(rect)
        # Arco
        percent = (self.value - self.min_value) / (self.max_value - self.min_value)
        percent = max(0, min(1, percent))
        angle = int(360 * percent)
        pen = QPen(self.color, 16)
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, -angle * 16)
        # Texto valor
        painter.setPen(QColor('#fff'))
        font = QFont('Arial', 22, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{int(self.value)}")
        # Unidad
        font2 = QFont('Arial', 12)
        painter.setFont(font2)
        painter.drawText(rect.adjusted(0, 40, 0, 0), Qt.AlignmentFlag.AlignHCenter, self.unit)
        # Label
        font3 = QFont('Arial', 11, QFont.Weight.Bold)
        painter.setFont(font3)
        painter.setPen(QColor('#00e676'))
        painter.drawText(rect.adjusted(0, -40, 0, 0), Qt.AlignmentFlag.AlignHCenter, self.label)

class DashboardExperimentalV2(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚗 OBD-II Dashboard Experimental UI v2")
        self.setMinimumSize(1100, 650)
        self.elm327 = OptimizedELM327Connection()
        self.logger = DataLogger()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gauges)
        self.slow_timer = QTimer()
        self.slow_timer.timeout.connect(self.update_log)
        self._setup_palette()
        self._build_ui()
        self._connect_signals()
    def _setup_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor('#181c20'))
        palette.setColor(QPalette.ColorRole.WindowText, QColor('#fff'))
        self.setPalette(palette)
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        # Panel central de gauges
        gauges_panel = QVBoxLayout()
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
        gauges_panel.addLayout(top)
        # Gauges circulares
        gauges_row = QHBoxLayout()
        self.gauges = {}
        self.gauges['010C'] = CircularGauge("RPM", "RPM", 0, 8000, '#00bcd4')
        self.gauges['010D'] = CircularGauge("Velocidad", "km/h", 0, 250, '#ffeb3b')
        self.gauges['0105'] = CircularGauge("Temp Motor", "°C", -40, 150, '#ff5722')
        self.gauges['0104'] = CircularGauge("Carga Motor", "%", 0, 100, '#8bc34a')
        self.gauges['0111'] = CircularGauge("Acelerador", "%", 0, 100, '#e040fb')
        for g in self.gauges.values():
            gauges_row.addWidget(g)
        gauges_panel.addLayout(gauges_row)
        main.addLayout(gauges_panel, 3)
        # Panel lateral de logs/eventos
        side_panel = QVBoxLayout()
        lbl = QLabel("Eventos OBD-II")
        lbl.setStyleSheet("color:#00e676; font-size:16px; font-weight:bold;")
        side_panel.addWidget(lbl)
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("background:#222; color:#fff; font-size:13px;")
        side_panel.addWidget(self.log_list, stretch=1)
        main.addLayout(side_panel, 1)
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
        for pid in self.gauges:
            info = self.elm327.query_pid(pid)
            if info:
                self.gauges[pid].set_value(info['value'])
                self._log_event(pid, info)
    def update_log(self):
        data = self.elm327.read_slow_data()
        if data:
            for pid, info in data.items():
                self._log_event(pid, info)
    def _log_event(self, pid, info):
        now = datetime.now().strftime("%H:%M:%S")
        msg = f"[{now}] {info['name']} ({pid}): {info['value']} {info['unit']}"
        self.log_list.addItem(msg)
        self.log_list.scrollToBottom()

def main():
    app = QApplication(sys.argv)
    win = DashboardExperimentalV2()
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
