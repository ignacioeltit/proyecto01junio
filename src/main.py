"""
Dashboard OBD-II Optimizado para conexión WiFi
"""
import sys
import logging
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer

from src.connection.elm327 import OptimizedELM327Connection
from src.ui.components import PIDCheckboxPanel, DataDisplayPanel
from src.utils.constants import DEFAULT_CONFIG

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class HighSpeedOBDDashboard(QMainWindow):
    """Ventana principal del dashboard"""
    def __init__(self):
        super().__init__()
        self.elm327 = OptimizedELM327Connection()
        self.timer = QTimer()
        self.slow_timer = QTimer()
        self.actual_speed = 0
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """Configura la interfaz de usuario"""
        self.setWindowTitle("Dashboard OBD-II")
        self.setMinimumSize(800, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Paneles de selección de PIDs
        self.pid_panel = PIDCheckboxPanel("PIDs Principales", self.elm327.fast_pids)
        self.slow_pid_panel = PIDCheckboxPanel("PIDs Secundarios", self.elm327.slow_pids)
        
        # Paneles de visualización
        self.data_panel = DataDisplayPanel("Datos en Tiempo Real", self.elm327.fast_pids)
        self.slow_data_panel = DataDisplayPanel("Datos Secundarios", self.elm327.slow_pids)
        
        # Agregar widgets al layout
        layout.addWidget(self.pid_panel)
        layout.addWidget(self.slow_pid_panel)
        layout.addWidget(self.data_panel)
        layout.addWidget(self.slow_data_panel)

    def setup_connections(self):
        """Configura las conexiones de señales"""
        self.timer.timeout.connect(self.update_fast_data)
        self.slow_timer.timeout.connect(self.update_slow_data)

    def update_fast_data(self):
        """Actualiza los datos principales"""
        for pid in self.pid_panel.get_selected_pids():
            value = self.elm327.get_pid_value(pid)
            self.data_panel.update_value(pid, value)

    def update_slow_data(self):
        """Actualiza los datos secundarios"""
        for pid in self.slow_pid_panel.get_selected_pids():
            value = self.elm327.get_pid_value(pid)
            self.slow_data_panel.update_value(pid, value)

def main():
    """Función principal de la aplicación"""
    try:
        app = QApplication(sys.argv)
        window = HighSpeedOBDDashboard()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Error al iniciar la aplicación: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
