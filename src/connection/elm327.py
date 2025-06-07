"""
Módulo para manejar la conexión con el dispositivo ELM327
"""
import socket
import logging
from ..utils.constants import OPERATION_MODES

class OptimizedELM327Connection:
    """Clase para manejar la conexión con el dispositivo ELM327"""
    
    def __init__(self):
        self.socket = None
        self.ip = "192.168.0.10"  # IP por defecto
        self.port = 35000
        self._mode = OPERATION_MODES["WIFI"]
        self.connected = False
        self.fast_pids = {
            '010C': {'name': 'RPM', 'value': 0, 'unit': 'RPM'},
            '010D': {'name': 'Velocidad', 'value': 0, 'unit': 'km/h'},
            '0105': {'name': 'Temp_Motor', 'value': 0, 'unit': '°C'},
            '0104': {'name': 'Carga_Motor', 'value': 0, 'unit': '%'},
            '0111': {'name': 'Acelerador', 'value': 0, 'unit': '%'}
        }
        self.slow_pids = {
            '010F': {'name': 'Temp_Admision', 'value': 0, 'unit': '°C'},
            '012F': {'name': 'Combustible', 'value': 0, 'unit': '%'},
            '0142': {'name': 'Voltaje', 'value': 0, 'unit': 'V'},
            '010B': {'name': 'Presion_MAP', 'value': 0, 'unit': 'kPa'}
        }
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establece conexión con el dispositivo"""
        if self._mode == OPERATION_MODES["EMULATOR"]:
            self.connected = True
            return True
            
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2)  # 2 segundos de timeout
            self.socket.connect((self.ip, self.port))
            self.connected = True
            # Inicialización
            self._send_command("ATZ")  # Reset
            self._send_command("ATE0")  # Echo off
            self._send_command("ATL0")  # Linefeeds off
            self._send_command("ATS0")  # Spaces off
            return True
        except Exception as e:
            self.logger.error(f"Error de conexión: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Desconecta del dispositivo"""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                self.logger.error(f"Error al desconectar: {e}")
            finally:
                self.socket = None
                self.connected = False
