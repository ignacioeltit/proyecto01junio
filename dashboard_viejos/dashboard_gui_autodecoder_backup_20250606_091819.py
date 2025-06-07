import sys
import os
import json
import logging
import socket
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout,
    QGroupBox, QLabel, QMessageBox, QComboBox
)
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QCloseEvent

# Agregar el directorio src al path si existe
if os.path.exists('src'):
    sys.path.append('src')

try:
    # Importaciones básicas OBD
    from src.obd.connection import OBDConnection
    from src.obd.emulador import EmuladorOBD
    from src.utils.logging_app import setup_logging

    # Importaciones para autodetección y decodificador universal
    from src.obd.protocol_detector import ProtocolDetector
    from src.obd.pid_decoder import PIDDecoder, get_supported_pids
except ImportError as e:
    print(f"🔧 Usando implementaciones básicas... Error: {e}")
    from obd_connection import OBDConnection
    from obd_emulador import EmuladorOBD
    from utils.logging_app import setup_logging

# Configuración del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class DashboardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Configuración de la ventana principal
        self.setWindowTitle("Dashboard OBD-II")
        self.setGeometry(100, 100, 800, 600)

        # Inicializar conexión OBD
        self.obd_connection = None
        self.init_obd_connection()

        # Configurar UI
        self.init_ui()

    def init_obd_connection(self):
        # Intentar conexión OBD
        try:
            self.obd_connection = OBDConnection()
            self.obd_connection.connect()
            logger.info("Conexión OBD establecida.")
        except Exception as e:
            logger.error(f"Error al conectar OBD: {e}")
            QMessageBox.critical(self, "Error de conexión", f"No se pudo conectar al dispositivo OBD-II: {e}")

    def init_ui(self):
        # Configuración de la interfaz de usuario
        # ...widgets y layout...
        self.show()

    def closeEvent(self, event):
        # Manejar evento de cierre
        if self.obd_connection:
            self.obd_connection.disconnect()
            logger.info("Conexión OBD cerrada.")
        event.accept()

class OBDDataSource(QObject):
    data_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    mode_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.connection = None
        self.emulator = None
        self.connection_mode = "emulator"
        self.selected_pids = []
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        self.usb_port = "COM3"
        self.wifi_ip = "192.168.0.10"
        self.wifi_port = 35000
        self.pid_decoder = PIDDecoder()
        self.supported_pids = []
        self.profile_path = None  # Ruta a perfil propietario si se desea cargar

    def autodetect_protocol_and_scan_pids(self):
        # Autodetectar protocolo y escanear PIDs soportados
        detector = ProtocolDetector(self.connection)
        protocol, success, _ = detector.autodetect_protocol()
        if not success:
            self.status_changed.emit("❌ No se pudo autodetectar protocolo OBD-II")
            return False
        self.status_changed.emit(f"✅ Protocolo detectado: {protocol}")
        self.supported_pids = get_supported_pids(self.connection)
        if not self.supported_pids:
            self.status_changed.emit("❌ No se detectaron PIDs soportados")
            return False
        self.status_changed.emit(f"✅ PIDs soportados: {', '.join(self.supported_pids)}")
        self.selected_pids = self.supported_pids[:8]  # Mostrar los primeros 8 por defecto
        return True

    def load_profile(self, profile_path):
        self.profile_path = profile_path
        self.pid_decoder.load_profile(profile_path)
        self.status_changed.emit(f"Perfil propietario cargado: {profile_path}")

    def connect(self):
        print(f"🔌 CONECTANDO EN MODO: {self.connection_mode}")
        try:
            if self.connection_mode == "emulator":
                print("🤖 Inicializando EMULADOR...")
                self.emulator = EmuladorOBD()
                self.is_connected = True
                self.status_changed.emit("✅ Conectado (EMULADOR)")
                return True
            elif self.connection_mode == "wifi":
                print(f"📡 Inicializando WIFI {self.wifi_ip}:{self.wifi_port}...")
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(3)
                test_result = test_sock.connect_ex((self.wifi_ip, self.wifi_port))
                test_sock.close()
                if test_result != 0:
                    error_msg = f"❌ No hay conectividad TCP a {self.wifi_ip}:{self.wifi_port}"
                    print(error_msg)
                    self.status_changed.emit(error_msg)
                    return False
                self.connection = OBDConnection(
                    mode="wifi",
                    ip=self.wifi_ip,
                    tcp_port=self.wifi_port,
                    timeout=5
                )
                if self.connection.connect():
                    self.is_connected = True
                    success_msg = f"✅ Conectado (WIFI {self.wifi_ip}:{self.wifi_port})"
                    print(success_msg)
                    self.status_changed.emit(success_msg)
                    # Autodetectar protocolo y escanear PIDs
                    if not self.autodetect_protocol_and_scan_pids():
                        return False
                    return True
                else:
                    error_msg = "❌ Falló conexión OBD WiFi"
                    print(error_msg)
                    self.status_changed.emit(error_msg)
                    return False
            elif self.connection_mode == "usb":
                print(f"🔌 Inicializando USB {self.usb_port}...")
                self.status_changed.emit("⚠️ USB no implementado aún")
                return False
        except Exception as e:
            error_msg = f"💥 ERROR: {e}"
            print(error_msg)
            self.status_changed.emit(error_msg)
            return False

    def read_data(self):
        if not self.is_connected:
            return {}
        data = {}
        if self.connection_mode == "emulator" and self.emulator:
            # ...existing code...
            return data
        elif self.connection_mode == "wifi" and self.connection:
            # Leer solo los PIDs soportados
            raw_data = self.connection.read_data(self.selected_pids)
            for pid, raw in raw_data.items():
                # Decodificar usando el decodificador universal/personalizado
                decoded = self.pid_decoder.decode(pid, [raw] if isinstance(raw, int) else raw)
                data[pid] = decoded['value']
            self.data_received.emit(data)
            return data
        else:
            return {}

# Funciones adicionales para escaneo de PIDs y decodificador
def scan_pids(connection):
    # ...código para escanear PIDs soportados...
    pass

def universal_decoder(data):
    # ...código para decodificación universal...
    pass

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = DashboardApp()
    sys.exit(app.exec())
