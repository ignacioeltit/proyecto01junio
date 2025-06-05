import socket
import time
from datetime import datetime
from src.utils.logging_app import log_evento_app
from src.obd.pids_ext import normalizar_pid

class ELM327WiFi:
    """
    Maneja la conexión y comunicación con ELM327 WiFi.
    """
    def __init__(self, ip="192.168.0.10", port=35000, timeout=10):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.connected = False

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.ip, self.port))
            log_evento_app("INFO", "Conexión TCP/IP establecida", "elm327_wifi")
            self._init_elm327()
            self.connected = True
            return True
        except Exception as e:
            log_evento_app("ERROR", f"Error de conexión: {e}", "elm327_wifi")
            self.connected = False
            return False

    def _init_elm327(self):
        init_commands = ["ATZ\r\n", "ATE0\r\n", "ATL0\r\n", "ATS0\r\n", "ATSP0\r\n"]
        for cmd in init_commands:
            self.send_command(cmd)
            time.sleep(0.3)

    def disconnect(self):
        try:
            if self.sock:
                self.sock.close()
                self.sock = None
            self.connected = False
            log_evento_app("INFO", "Desconectado de ELM327 WiFi", "elm327_wifi")
        except Exception as e:
            log_evento_app("ERROR", f"Error al desconectar: {e}", "elm327_wifi")

    def send_command(self, cmd):
        try:
            if not self.connected:
                raise Exception("No conectado")
            self.sock.sendall(cmd.encode())
            time.sleep(0.2)
            data = self.sock.recv(128).decode(errors="ignore")
            log_evento_app("DEBUG", f"Comando enviado: {cmd.strip()} | Respuesta: {data.strip()}", "elm327_wifi")
            return data
        except Exception as e:
            log_evento_app("ERROR", f"Fallo al enviar comando: {e}", "elm327_wifi")
            return ""

    def read_pid(self, pid):
        pid = normalizar_pid(pid)
        cmd = ""
        if pid == "rpm":
            cmd = "010C\r"
        elif pid == "vel":
            cmd = "010D\r"
        elif pid == "temp":
            cmd = "0105\r"
        else:
            return None
        response = self.send_command(cmd)
        if pid == "rpm":
            return self.parse_rpm(response)
        elif pid == "vel":
            return self.parse_speed(response)
        elif pid == "temp":
            return self.parse_temperature(response)

    def parse_rpm(self, response):
        # "41 0C XX XX" -> RPM = ((A*256)+B)/4
        try:
            if "41 0C" in response:
                parts = response.split()
                idx = parts.index("0C")
                A = int(parts[idx+1], 16)
                B = int(parts[idx+2], 16)
                return ((A * 256) + B) // 4
        except Exception as e:
            log_evento_app("ERROR", f"Parseo RPM: {e}", "elm327_wifi")
        return None

    def parse_speed(self, response):
        # "41 0D XX" -> Velocidad = A km/h
        try:
            if "41 0D" in response:
                parts = response.split()
                idx = parts.index("0D")
                A = int(parts[idx+1], 16)
                return A
        except Exception as e:
            log_evento_app("ERROR", f"Parseo Velocidad: {e}", "elm327_wifi")
        return None

    def parse_temperature(self, response):
        # "41 05 XX" -> Temperatura = A-40 °C
        try:
            if "41 05" in response:
                parts = response.split()
                idx = parts.index("05")
                A = int(parts[idx+1], 16)
                return A - 40
        except Exception as e:
            log_evento_app("ERROR", f"Parseo Temp: {e}", "elm327_wifi")
        return None

    def get_data(self):
        """
        Retorna un dict con los datos principales.
        """
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "rpm": self.read_pid("rpm"),
            "vel": self.read_pid("vel"),
            "temp": self.read_pid("temp"),
            "escenario": "wifi_real"
        }

def test_wifi_connection():
    elm = ELM327WiFi()
    if elm.connect():
        print(elm.get_data())
        elm.disconnect()
    else:
        print("No se pudo conectar al ELM327 WiFi.")
