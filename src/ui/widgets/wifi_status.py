from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtCore import pyqtSignal

class WiFiStatusWidget(QWidget):
    estado_cambiado = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.label = QLabel("WiFi: Desconectado")
        self.label.setStyleSheet("color: #e53935; font-weight: bold;")
        self.last_update = QLabel("Último dato: --")
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.last_update)
        self.setLayout(layout)
        self.setFixedHeight(32)

    def set_estado(self, estado, ip="192.168.0.10"):
        if estado == "conectado":
            self.label.setText(f"WiFi: Conectado ({ip})")
            self.label.setStyleSheet("color: #43a047; font-weight: bold;")
        else:
            self.label.setText("WiFi: Desconectado")
            self.label.setStyleSheet("color: #e53935; font-weight: bold;")
        self.estado_cambiado.emit(estado)

    def actualizar_timestamp(self, ts):
        self.last_update.setText(f"Último dato: {ts}")
