# Manejo de conexión OBD-II (WiFi/USB)

import serial
import socket


class OBDConnection:
    def __init__(
        self, mode="usb", port=None, baudrate=38400, ip=None, tcp_port=None, timeout=2
    ):
        self.mode = mode
        self.port = port
        self.baudrate = baudrate
        self.ip = ip
        self.tcp_port = tcp_port
        self.timeout = timeout
        self.connection = None

    def connect(self):
        if self.mode == "usb":
            self.connection = serial.Serial(
                self.port, self.baudrate, timeout=self.timeout
            )
        elif self.mode == "wifi":
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(self.timeout)
            self.connection.connect((self.ip, self.tcp_port))
        else:
            raise ValueError("Modo de conexión no soportado")
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def disconnect(self):
        """Cierra la conexión actual"""
        if not self.connection:
            return

        try:
            if self.mode == "usb":
                self.connection.close()
            elif self.mode == "wifi":
                self.connection.close()
            self.connection = None
        except Exception as e:
            print(f"Error al cerrar conexión: {e}")

    def write(self, data):
        """Envía datos a través de la conexión"""
        if not self.connection:
            return False

        try:
            if self.mode == "usb":
                self.connection.write(data.encode())
            else:
                self.connection.send(data.encode())
            return True
        except Exception as e:
            print(f"Error escribiendo datos: {e}")
            return False

    def read(self, size=128):
        """Lee datos de la conexión"""
        if not self.connection:
            return None

        try:
            if self.mode == "usb":
                data = self.connection.read(size)
            else:
                data = self.connection.recv(size)
            return data.decode(errors="ignore")
        except Exception as e:
            print(f"Error leyendo datos: {e}")
            return None
