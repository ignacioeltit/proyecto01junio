# Comunicación con ELM327
from .connection import OBDConnection
import time


class ELM327:
    def __init__(self, connection: OBDConnection):
        self.connection = connection

    def initialize(self):
        # Secuencia básica de inicialización ELM327
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
        return self.connection.read(128)

    def send_pid(self, pid_cmd):
        self.connection.write(pid_cmd + "\r")
        time.sleep(0.1)
        return self.connection.read(128)
