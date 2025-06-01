# Manejo de conexión OBD-II (WiFi/USB)

import serial
import socket


class OBDConnection:
    def __init__(self, mode='usb', port=None, baudrate=38400, ip=None,
                 tcp_port=None, timeout=2):
        self.mode = mode
        self.port = port
        self.baudrate = baudrate
        self.ip = ip
        self.tcp_port = tcp_port
        self.timeout = timeout
        self.connection = None

    def connect(self):
        if self.mode == 'usb':
            self.connection = serial.Serial(
                self.port, self.baudrate, timeout=self.timeout
            )
        elif self.mode == 'wifi':
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(self.timeout)
            self.connection.connect((self.ip, self.tcp_port))
        else:
            raise ValueError('Modo de conexión no soportado')
        return self.connection

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def write(self, data):
        if self.mode == 'usb':
            self.connection.write(data.encode())
        elif self.mode == 'wifi':
            self.connection.sendall(data.encode())

    def read(self, size=128):
        if self.mode == 'usb':
            return self.connection.read(size).decode(errors='ignore')
        elif self.mode == 'wifi':
            return self.connection.recv(size).decode(errors='ignore')
