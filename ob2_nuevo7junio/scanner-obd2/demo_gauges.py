# demo_gauges.py
# Script de prueba visual para SimpleGaugeWidget en modo demo (sin OBD2)
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PySide6.QtCore import QTimer
import sys
import math
import random
from ui.widgets.simple_gauge import SimpleGaugeWidget

class DemoGaugesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo Gauges Racing - Modo Test")
        self.setStyleSheet("background: #222;")
        layout = QVBoxLayout(self)
        self.gauges = []
        # Ejemplo de gauges típicos
        self.gauges.append(SimpleGaugeWidget("RPM", 0, 8000, "rpm"))
        self.gauges.append(SimpleGaugeWidget("Velocidad", 0, 240, "km/h"))
        self.gauges.append(SimpleGaugeWidget("Temp Agua", 40, 120, "°C"))
        self.gauges.append(SimpleGaugeWidget("Presión Aceite", 0, 100, "psi"))
        gauges_layout = QHBoxLayout()
        for g in self.gauges:
            gauges_layout.addWidget(g)
        layout.addLayout(gauges_layout)
        self.setLayout(layout)
        # Timer para animar valores demo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_gauges)
        self.timer.start(60)
        self.t = 0
    def update_gauges(self):
        self.t += 0.06
        # Simulación tipo onda y random
        self.gauges[0].set_value(4000 + 3500 * math.sin(self.t))  # RPM
        self.gauges[1].set_value(120 + 100 * math.sin(self.t/2))  # Velocidad
        self.gauges[2].set_value(80 + 30 * math.sin(self.t/3))    # Temp Agua
        self.gauges[3].set_value(40 + 30 * abs(math.sin(self.t/1.5)))  # Presión Aceite

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoGaugesWindow()
    win.resize(900, 320)
    win.show()
    sys.exit(app.exec())
