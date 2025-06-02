import sys
import math
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class EmuladorOBD2GUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Emulador OBD-II Avanzado')
        self.setGeometry(200, 200, 420, 320)
        self.modo = 'ralenti'
        self.falla = None
        self.rpm = 800
        self.velocidad = 0
        self.t = 0
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.simular)
        self.timer.start(1000)

    def init_ui(self):
        layout = QVBoxLayout()
        self.status = QLabel()
        self.status.setFont(QFont('Arial', 14))
        layout.addWidget(self.status)

        # Selector de modo
        modos = ['ralenti', 'ciudad', 'carretera', 'falla']
        self.combo_modo = QComboBox()
        self.combo_modo.addItems(modos)
        self.combo_modo.currentTextChanged.connect(self.cambiar_modo)
        layout.addWidget(QLabel('Modo de conducción:'))
        layout.addWidget(self.combo_modo)

        # Selector de falla
        fallas = ['Sin Falla', 'sensor_rpm', 'sensor_vel', 'dtc']
        self.combo_falla = QComboBox()
        self.combo_falla.addItems(fallas)
        self.combo_falla.currentTextChanged.connect(self.cambiar_falla)
        layout.addWidget(QLabel('Falla simulada:'))
        layout.addWidget(self.combo_falla)

        # Sliders para manipular valores en modo "falla"
        self.slider_rpm = QSlider(Qt.Orientation.Horizontal)
        self.slider_rpm.setMinimum(0)
        self.slider_rpm.setMaximum(8000)
        self.slider_rpm.setValue(800)
        self.slider_rpm.setTickInterval(100)
        self.slider_rpm.valueChanged.connect(self.actualizar_status)
        layout.addWidget(QLabel('RPM (solo modo falla):'))
        layout.addWidget(self.slider_rpm)

        self.slider_vel = QSlider(Qt.Orientation.Horizontal)
        self.slider_vel.setMinimum(0)
        self.slider_vel.setMaximum(200)
        self.slider_vel.setValue(0)
        self.slider_vel.setTickInterval(5)
        self.slider_vel.valueChanged.connect(self.actualizar_status)
        layout.addWidget(QLabel('Velocidad (solo modo falla):'))
        layout.addWidget(self.slider_vel)

        self.setLayout(layout)
        self.actualizar_status()

    def cambiar_modo(self, modo):
        self.modo = modo
        self.t = 0
        self.actualizar_status()

    def cambiar_falla(self, falla):
        self.falla = None if falla == 'Sin Falla' else falla
        self.actualizar_status()

    def simular(self):
        self.t += 1
        if self.modo == 'ralenti':
            self.rpm = 800 + random.randint(-20, 20)
            self.velocidad = 0
        elif self.modo == 'ciudad':
            self.rpm = 900 + int(1200 * abs(math.sin(self.t/15))) + random.randint(-50, 50)
            if self.t % 40 < 10:
                self.velocidad = 0
            elif self.t % 40 < 30:
                self.velocidad = min(60, self.velocidad + random.randint(0, 4))
            else:
                self.velocidad = max(0, self.velocidad - random.randint(0, 6))
        elif self.modo == 'carretera':
            self.rpm = 2200 + int(600 * abs(math.sin(self.t/30))) + random.randint(-40, 40)
            self.velocidad = 90 + int(30 * abs(math.sin(self.t/20))) + random.randint(-5, 5)
        elif self.modo == 'falla':
            if self.falla == 'sensor_rpm':
                self.rpm = self.slider_rpm.value()
            elif self.falla == 'sensor_vel':
                self.velocidad = self.slider_vel.value()
            elif self.falla == 'dtc':
                self.rpm = 1200
                self.velocidad = 30
            else:
                self.rpm = self.slider_rpm.value()
                self.velocidad = self.slider_vel.value()
        self.actualizar_status()

    def actualizar_status(self):
        self.status.setText(f"<b>Modo:</b> {self.modo} | <b>RPM:</b> {self.rpm} | <b>Velocidad:</b> {self.velocidad} km/h | <b>Falla:</b> {self.falla or 'Ninguna'}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = EmuladorOBD2GUI()
    win.show()
    sys.exit(app.exec())
