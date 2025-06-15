import sys
import threading
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QSlider, QHBoxLayout, QLineEdit
)
from PyQt6.QtCore import Qt

class ElmSimulatorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulador ELM327 - All Motors")
        self.setMinimumWidth(400)

        self.layout = QVBoxLayout()

        # Botón para lanzar el emulador
        self.start_button = QPushButton("Iniciar emulador")
        self.start_button.clicked.connect(self.run_emulator)
        self.layout.addWidget(self.start_button)

        # Mostrar el puerto generado
        self.port_label = QLabel("Puerto generado:")
        self.port_output = QLineEdit()
        self.port_output.setReadOnly(True)
        self.layout.addWidget(self.port_label)
        self.layout.addWidget(self.port_output)

        # Sliders para simular PIDs
        self.add_slider("RPM", 0, 8000)
        self.add_slider("Temperatura (°C)", -40, 150)
        self.add_slider("Velocidad (km/h)", 0, 250)

        self.setLayout(self.layout)

    def add_slider(self, name, min_val, max_val):
        container = QHBoxLayout()
        label = QLabel(f"{name}:")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue((min_val + max_val) // 2)
        value_display = QLineEdit(str(slider.value()))
        value_display.setReadOnly(True)

        # Actualizar valor en campo
        slider.valueChanged.connect(lambda v: value_display.setText(str(v)))

        container.addWidget(label)
        container.addWidget(slider)
        container.addWidget(value_display)
        self.layout.addLayout(container)

    def run_emulator(self):
        def launch():
            try:
                elm_path = "/Users/ignacioeltit/Library/Python/3.9/bin/elm"  # Ruta completa al ejecutable instalado
                process = subprocess.Popen([elm_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in process.stdout:
                    if "pseudo-tty" in line:
                        port = line.strip().split(":")[-1].strip()
                        self.port_output.setText(port)
            except Exception as e:
                self.port_output.setText(f"Error: {str(e)}")

        thread = threading.Thread(target=launch)
        thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ElmSimulatorGUI()
    window.show()
    sys.exit(app.exec())
