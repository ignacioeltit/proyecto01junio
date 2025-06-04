# Comunicación con ELM327
from .connection import OBDConnection
import time


class ELM327:
    def __init__(self, connection: OBDConnection):
        self.connection = connection

    def initialize(self):
        """
        Inicializa el ELM327 con comandos estándar. Devuelve True si responde correctamente.
        """
        self.connection.write("ATZ\r")  # Reset
        time.sleep(1)
        self.connection.write("ATE0\r")  # Echo Off
        time.sleep(0.1)
        self.connection.write("ATL0\r")  # Linefeeds Off
        time.sleep(0.1)
        self.connection.write("ATS0\r")  # Spaces Off
        time.sleep(0.1)
        self.connection.write("ATH0\r")  # Headers Off
        time.sleep(0.1)
        self.connection.write("ATSP0\r")  # Protocolo automático
        time.sleep(0.1)
        # Leer respuesta para confirmar comunicación
        resp = self.connection.read(128)
        return bool(resp and "OK" in resp.upper())

    def send_pid(self, pid_cmd):
        """
        Envía un comando PID OBD-II y retorna la respuesta cruda.
        """
        self.connection.write(pid_cmd + "\r")
        time.sleep(0.1)
        return self.connection.read(128)

    def read_dtc(self):
        """
        Lee los códigos DTC almacenados en la ECU. Devuelve una lista de códigos o un mensaje seguro si no implementado.
        """
        try:
            self.connection.write("03\r")
            time.sleep(0.1)
            resp = self.connection.read(128)
            if not resp or "NO DATA" in resp.upper():
                return []
            # Decodificación simple: retorna la respuesta cruda como lista
            return [resp.strip()]
        except Exception:
            return ["Error al leer DTC"]

    def clear_dtc(self):
        """
        Borra los códigos DTC almacenados en la ECU. Devuelve True si ejecutado, False si error.
        """
        try:
            self.connection.write("04\r")
            time.sleep(0.1)
            self.connection.read(128)
            return True
        except Exception:
            return False


# Versión consolidada, métodos corregidos, 2025-06-03
