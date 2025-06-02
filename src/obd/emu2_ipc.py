import sys
import math
import random
import multiprocessing
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class EmuladorDatos(multiprocessing.Process):
    def __init__(self, shared_dict):
        super().__init__()
        self.shared_dict = shared_dict
        self.running = True

    def run(self):
        t = 0
        while self.running:
            modo = self.shared_dict.get('modo', 'ralenti')
            falla = self.shared_dict.get('falla', None)
            if modo == 'ralenti':
                rpm = 800 + random.randint(-20, 20)
                vel = 0
            elif modo == 'ciudad':
                rpm = 900 + int(1200 * abs(math.sin(t/15))) + random.randint(-50, 50)
                if t % 40 < 10:
                    vel = 0
                elif t % 40 < 30:
                    vel = min(60, self.shared_dict.get('vel', 0) + random.randint(0, 4))
                else:
                    vel = max(0, self.shared_dict.get('vel', 0) - random.randint(0, 6))
            elif modo == 'carretera':
                rpm = 2200 + int(600 * abs(math.sin(t/30))) + random.randint(-40, 40)
                vel = 90 + int(30 * abs(math.sin(t/20))) + random.randint(-5, 5)
            elif modo == 'falla':
                if falla == 'sensor_rpm':
                    rpm = self.shared_dict.get('rpm', 0)
                    vel = self.shared_dict.get('vel', 0)
                elif falla == 'sensor_vel':
                    rpm = self.shared_dict.get('rpm', 0)
                    vel = self.shared_dict.get('vel', 0)
                else:
                    rpm = self.shared_dict.get('rpm', 0)
                    vel = self.shared_dict.get('vel', 0)
            else:
                rpm = 800
                vel = 0
            self.shared_dict['rpm'] = rpm
            self.shared_dict['vel'] = vel
            t += 1
            time.sleep(1)

    def stop(self):
        self.running = False

class EmuladorGUI(QWidget):
    def __init__(self, shared_dict):
        super().__init__()
        self.shared_dict = shared_dict
        self.setWindowTitle('Emulador OBD-II (IPC)')
        self.setGeometry(200, 200, 420, 320)
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.actualizar_status)
        self.timer.start(500)

    def init_ui(self):
        layout = QVBoxLayout()
        self.status = QLabel()
        self.status.setFont(QFont('Arial', 14))
        layout.addWidget(self.status)
        modos = ['ralenti', 'ciudad', 'carretera', 'falla']
        self.combo_modo = QComboBox()
        self.combo_modo.addItems(modos)
        self.combo_modo.currentTextChanged.connect(self.cambiar_modo)
        layout.addWidget(QLabel('Modo de conducción:'))
        layout.addWidget(self.combo_modo)
        fallas = ['Sin Falla', 'sensor_rpm', 'sensor_vel']
        self.combo_falla = QComboBox()
        self.combo_falla.addItems(fallas)
        self.combo_falla.currentTextChanged.connect(self.cambiar_falla)
        layout.addWidget(QLabel('Falla simulada:'))
        layout.addWidget(self.combo_falla)
        self.slider_rpm = QSlider(Qt.Orientation.Horizontal)
        self.slider_rpm.setMinimum(0)
        self.slider_rpm.setMaximum(8000)
        self.slider_rpm.setValue(800)
        self.slider_rpm.setTickInterval(100)
        self.slider_rpm.valueChanged.connect(self.cambiar_rpm)
        layout.addWidget(QLabel('RPM (solo modo falla):'))
        layout.addWidget(self.slider_rpm)
        self.slider_vel = QSlider(Qt.Orientation.Horizontal)
        self.slider_vel.setMinimum(0)
        self.slider_vel.setMaximum(200)
        self.slider_vel.setValue(0)
        self.slider_vel.setTickInterval(5)
        self.slider_vel.valueChanged.connect(self.cambiar_vel)
        layout.addWidget(QLabel('Velocidad (solo modo falla):'))
        layout.addWidget(self.slider_vel)
        self.setLayout(layout)
        self.actualizar_status()

    def cambiar_modo(self, modo):
        self.shared_dict['modo'] = modo
        self.actualizar_status()

    def cambiar_falla(self, falla):
        self.shared_dict['falla'] = None if falla == 'Sin Falla' else falla
        self.actualizar_status()

    def cambiar_rpm(self, val):
        self.shared_dict['rpm'] = val
        self.actualizar_status()

    def cambiar_vel(self, val):
        self.shared_dict['vel'] = val
        self.actualizar_status()

    def actualizar_status(self):
        modo = self.shared_dict.get('modo', 'ralenti')
        rpm = self.shared_dict.get('rpm', 800)
        vel = self.shared_dict.get('vel', 0)
        falla = self.shared_dict.get('falla', None)
        self.status.setText(f"<b>Modo:</b> {modo} | <b>RPM:</b> {rpm} | <b>Velocidad:</b> {vel} km/h | <b>Falla:</b> {falla or 'Ninguna'}")

if __name__ == '__main__':
    manager = multiprocessing.Manager()
    shared_dict = manager.dict({'modo': 'ralenti', 'falla': None, 'rpm': 800, 'vel': 0})
    emu_proc = EmuladorDatos(shared_dict)
    emu_proc.start()
    app = QApplication(sys.argv)
    win = EmuladorGUI(shared_dict)
    win.show()
    app.exec()
    emu_proc.terminate()
    emu_proc.join()
