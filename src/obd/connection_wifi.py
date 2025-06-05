from .elm327_wifi import ELM327WiFi
from src.utils.logging_app import log_evento_app
from datetime import datetime

class OBDConnectionWiFi:
    """Conexión WiFi compatible con el sistema OBD existente"""
    def __init__(self, ip="192.168.0.10", port=35000):
        self.ip = ip
        self.port = port
        self.elm_wifi = None
        self.connected = False
        self.modo = "wifi"

    def connect(self):
        """Conectar usando ELM327 WiFi"""
        try:
            self.elm_wifi = ELM327WiFi(self.ip, self.port)
            success = self.elm_wifi.connect()
            self.connected = success
            if success:
                log_evento_app("INFO", "Conexión WiFi establecida", contexto="wifi_connection")
            return success
        except Exception as e:
            log_evento_app("ERROR", f"Error en conexión WiFi: {e}", contexto="wifi_connection")
            return False

    def read_data(self, pids):
        """Leer datos usando ELM327 WiFi - Compatible con dashboard existente"""
        if not self.elm_wifi or not self.elm_wifi.connected:
            log_evento_app("WARNING", "Intento de lectura sin conexión WiFi", contexto="wifi_read")
            return {}
        try:
            # Se espera que ELM327WiFi tenga un método read_all_data()
            data = self.elm_wifi.get_data() if hasattr(self.elm_wifi, 'get_data') else {}
            if data:
                data['escenario'] = 'wifi_real'
                log_evento_app("INFO", f"Datos WiFi leídos: {len(data)} parámetros", contexto="wifi_read")
                return data
            else:
                log_evento_app("WARNING", "No se recibieron datos del ELM327 WiFi", contexto="wifi_read")
                return {}
        except Exception as e:
            log_evento_app("ERROR", f"Error leyendo datos WiFi: {e}", contexto="wifi_read")
            return {}

    def disconnect(self):
        """Desconectar ELM327 WiFi"""
        if self.elm_wifi:
            self.elm_wifi.disconnect()
        self.connected = False
        log_evento_app("INFO", "Conexión WiFi cerrada", contexto="wifi_connection")
