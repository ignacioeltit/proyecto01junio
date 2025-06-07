import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QGridLayout, QComboBox
from PyQt6.QtCore import QTimer
from obd_connection import OptimizedELM327Connection, OPERATION_MODES
from data_logger import DataLogger
from ui_panels import PIDCheckboxPanel

class HighSpeedOBDDashboard(QMainWindow):
    # ...existing code (solo la lógica de UI y señales, usando los módulos importados)...
    pass

def main():
    try:
        app = QApplication(sys.argv)
        window = HighSpeedOBDDashboard()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error al iniciar la aplicación: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
