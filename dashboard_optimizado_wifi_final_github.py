"""
Dashboard OBD-II Optimizado para conexión WiFi
"""
import sys
import os
import random
import time
import csv
import logging
import socket
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QGridLayout, QComboBox,
    QCheckBox, QScrollArea, QTabWidget
)
from PyQt6.QtCore import QTimer

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Modos de operación
OPERATION_MODES = {
    "WIFI": "wifi",
    "EMULATOR": "emulator"
}


class PIDCheckboxPanel(QGroupBox):
    """Panel de checkboxes para selección de PIDs"""
    def __init__(self, title: str, pids: dict) -> None:
        super().__init__(title)
        self.checkboxes = {}
        self.setup_ui(pids)

    def setup_ui(self, pids: dict) -> None:
        """Configura la interfaz del panel"""
        layout = QGridLayout()
        row = 0
        col = 0
        
        for pid, info in pids.items():
            checkbox = QCheckBox(f"{info['name']} ({info['unit']})")
            self.checkboxes[pid] = checkbox
            layout.addWidget(checkbox, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        self.setLayout(layout)

    def get_selected_pids(self) -> list:
        """Retorna lista de PIDs seleccionados"""
        return [pid for pid, checkbox in self.checkboxes.items() 
                if checkbox.isChecked()]

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
        # --- NUEVO: PIDs extendidos agrupados por familia ---
        self.extended_pid_families = {
            'Transmisión': {
                '221910': {'name': 'Trans Fluid Temp', 'unit': 'C', 'equation': lambda A, B=None: A-40, 'header': '7E0'},
                '221A00': {'name': 'Trans Output Shaft Speed', 'unit': 'rpm', 'equation': lambda A,B: (A*256+B), 'header': '7E1'},
                '221A02': {'name': 'Trans Input Shaft Speed', 'unit': 'rpm', 'equation': lambda A,B: (A*256+B), 'header': '7E1'},
                '221A08': {'name': 'Trans Torque Converter Slip', 'unit': 'rpm', 'equation': lambda A,B: (A*256+B), 'header': '7E1'},
                '22191A': {'name': 'Trans Fluid Pressure', 'unit': 'bar', 'equation': lambda A,B: (A*256+B)/100, 'header': '7E1'},
                '22190E': {'name': 'Transmission Fluid Level', 'unit': 'L', 'equation': lambda A,B: (A*256+B)/100, 'header': '7E1'},
            },
            'Motor': {
                '221136': {'name': 'Engine Oil Temp', 'unit': 'C', 'equation': lambda A,B=None: A-40, 'header': '7E0'},
                '22111C': {'name': 'Oil Pressure', 'unit': 'kPa', 'equation': lambda A,B=None: A*4, 'header': '7E0'},
                '221134': {'name': 'Battery Voltage', 'unit': 'V', 'equation': lambda A,B=None: A/10, 'header': '7E0'},
                '22201D': {'name': 'Engine Torque', 'unit': 'Nm', 'equation': lambda A,B: (A*256+B)/8, 'header': '7E0'},
                '221138': {'name': 'Oil Life Remaining', 'unit': '%', 'equation': lambda A,B=None: A, 'header': '7E0'},
                '015C': {'name': 'Engine Oil Temp (SAE)', 'unit': 'C', 'equation': lambda A,B=None: A-40, 'header': '7DF'},
            },
            'Inyectores': {
                '220298': {'name': 'Injector PW1', 'unit': 'us', 'equation': lambda A,B: A*256+B, 'header': '7E0'},
                '22029A': {'name': 'Injector PW2', 'unit': 'us', 'equation': lambda A,B: A*256+B, 'header': '7E0'},
                '22029C': {'name': 'Injector PW3', 'unit': 'us', 'equation': lambda A,B: A*256+B, 'header': '7E0'},
                '22029E': {'name': 'Injector PW4', 'unit': 'us', 'equation': lambda A,B: A*256+B, 'header': '7E0'},
                '2202A0': {'name': 'Injector PW5', 'unit': 'us', 'equation': lambda A,B: A*256+B, 'header': '7E0'},
                '2202A2': {'name': 'Injector PW6', 'unit': 'us', 'equation': lambda A,B: A*256+B, 'header': '7E0'},
                '2202A4': {'name': 'Injector PW7', 'unit': 'us', 'equation': lambda A,B: A*256+B, 'header': '7E0'},
                '2202A6': {'name': 'Injector PW8', 'unit': 'us', 'equation': lambda A,B: A*256+B, 'header': '7E0'},
            },
            'Encendido': {
                '2220CB': {'name': 'Knock Retard', 'unit': '°', 'equation': lambda A,B: ((A*256)+B)*0.05, 'header': '7E0'},
            },
            'Caja Transferencia y Diferencial': {
                '221A10': {'name': 'Transfer Case Oil Temp', 'unit': 'C', 'equation': lambda A,B=None: A-40, 'header': '7E1'},
                '22110A': {'name': 'Differential Oil Temp', 'unit': 'C', 'equation': lambda A,B=None: A-40, 'header': '7E1'},
            },
            'ABS': {
                '224901': {'name': 'ABS Wheel Speed FL', 'unit': 'km/h', 'equation': lambda A,B: (A*256+B)/100, 'header': '7E1'},
                '224903': {'name': 'ABS Wheel Speed FR', 'unit': 'km/h', 'equation': lambda A,B: (A*256+B)/100, 'header': '7E1'},
                '224905': {'name': 'ABS Wheel Speed RL', 'unit': 'km/h', 'equation': lambda A,B: (A*256+B)/100, 'header': '7E1'},
                '224907': {'name': 'ABS Wheel Speed RR', 'unit': 'km/h', 'equation': lambda A,B: (A*256+B)/100, 'header': '7E1'},
            },
            'Sensores Chasis': {
                '2216BC': {'name': 'Steering Angle', 'unit': 'deg', 'equation': lambda A,B: (A*256+B)/10, 'header': '7E0'},
                '2216A2': {'name': 'G-Force Lateral', 'unit': 'g', 'equation': lambda A,B: ((A*256+B)-20000)/1000, 'header': '7E0'},
                '2216A0': {'name': 'G-Force Longitudinal', 'unit': 'g', 'equation': lambda A,B: ((A*256+B)-20000)/1000, 'header': '7E0'},
                '2216A4': {'name': 'Yaw Rate', 'unit': 'deg/s', 'equation': lambda A,B: ((A*256+B)-20000)/100, 'header': '7E0'},
            },
            'Otros extendidos': {
                '22143': {'name': 'Barometric Pressure', 'unit': 'kPa', 'equation': lambda A,B=None: A, 'header': '7E0'},
                '221202': {'name': 'Manifold Absolute Pressure', 'unit': 'bar', 'equation': lambda A,B: (A*256+B)/100, 'header': '7E0'},
                '221A18': {'name': 'Gearbox Selected Gear', 'unit': 'N', 'equation': lambda A,B=None: A, 'header': '7E1'},
            },
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
            self._send_command("ATH0")  # Headers off
            self._send_command("ATSP0")  # Auto protocol
            return True
        except Exception as e:
            self.logger.error(f"Error de conexión: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Cierra la conexión"""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                self.logger.error(f"Error al desconectar: {e}")
            finally:
                self.socket = None
        self.connected = False

    def _send_command(self, cmd):
        """Envía un comando al dispositivo"""
        if not self.connected:
            return None
            
        if self._mode == OPERATION_MODES["EMULATOR"]:
            return self._emulate_response(cmd)
            
        try:
            cmd = cmd.encode() + b'\r\n'
            self.socket.send(cmd)
            
            response = ""
            start_time = time.time()
            
            while '>' not in response:
                chunk = self.socket.recv(256).decode('utf-8', errors='ignore')
                response += chunk
                if time.time() - start_time > 0.2:  # Timeout de 200ms
                    break
                    
            return response
        except Exception as e:
            self.logger.error(f"Error enviando comando: {e}")
            return None

    def _emulate_response(self, cmd):
        """Emula respuestas del dispositivo para pruebas"""
        if cmd.startswith("AT"):
            return "OK"

        random_data = {
            '010C': lambda: f"410C{random.randint(0, 255):02X}",
            '010D': lambda: f"410D{random.randint(0, 255):02X}",
            '0105': lambda: f"4105{random.randint(0, 255):02X}",
            '0104': lambda: f"4104{random.randint(0, 255):02X}",
            '0111': lambda: f"4111{random.randint(0, 255):02X}",
            '010F': lambda: f"410F{random.randint(0, 255):02X}",
            '012F': lambda: f"412F{random.randint(0, 255):02X}",
            '0142': lambda: f"4142{random.randint(0, 255):02X}",
            '010B': lambda: f"410B{random.randint(0, 255):02X}"
        }

        if cmd in random_data:
            return random_data[cmd]()
        return "NO DATA"

    def _get_tx_header(self, mode):
        """Obtiene el header correcto según el modo"""
        return '7E0' if mode in ['01', '22'] else '7DF'  # 7E0 para requests específicos, 7DF para broadcast

    def read_pid(self, pid):
        """Lee un PID específico"""
        if not self.connected:
            return None
            
        response = None
        tries = 0
        max_tries = 3
        
        while tries < max_tries:
            response = self._send_command(pid)
            if response and 'NO DATA' not in response:
                break
            tries += 1
            time.sleep(0.01)
            
        return response

    def read_fast_data(self):
        """Lee datos críticos a alta velocidad"""
        if not self.connected:
            return {}

        if self._mode == OPERATION_MODES["EMULATOR"]:
            return {
                '010C': {'name': 'RPM', 'value': 800 + random.randint(-50, 50), 'unit': 'RPM'},
                '010D': {'name': 'Velocidad', 'value': 60 + random.randint(-5, 5), 'unit': 'km/h'},
                '0105': {'name': 'Temp_Motor', 'value': 85 + random.randint(-2, 2), 'unit': '°C'},
                '0104': {'name': 'Carga_Motor', 'value': 20 + random.randint(-5, 5), 'unit': '%'},
                '0111': {'name': 'Acelerador', 'value': 15 + random.randint(-3, 3), 'unit': '%'},
            }

        data = {}
        
        try:
            # Limpiar buffer
            self.socket.settimeout(0.1)
            try:
                self.socket.recv(1024)
            except socket.timeout:
                pass

            # Restaurar timeout normal
            self.socket.settimeout(0.3)

            for pid in self.fast_pids:
                try:
                    self.socket.sendall(f"{pid}\r".encode())
                    response = ""
                    start_time = time.time()

                    while True:
                        try:
                            chunk = self.socket.recv(256).decode('utf-8', errors='ignore')
                            if chunk:
                                response += chunk

                            if '>' in response or time.time() - start_time > 0.2:
                                break

                        except socket.timeout:
                            break

                    if response:
                        parsed = self.parse_response(response, pid)
                        if parsed and self._validate_pid_value(pid, parsed['value']):
                            data[pid] = parsed

                except Exception as e:
                    print(f"Error leyendo PID {pid}: {e}")
                    continue

            return data

        except Exception as e:
            print(f"Error en read_fast_data: {e}")
            return {}

    def read_slow_data(self):
        """Lee datos adicionales a baja velocidad"""
        if not self.connected:
            return {}

        if self._mode == OPERATION_MODES["EMULATOR"]:
            return {
                '010F': {'name': 'Temp_Admision', 'value': 25 + random.randint(-2, 2), 'unit': '°C'},
                '012F': {'name': 'Combustible', 'value': 75 + random.randint(-5, 5), 'unit': '%'},
                '0142': {'name': 'Voltaje', 'value': 12.5 + random.uniform(-0.2, 0.2), 'unit': 'V'},
                '010B': {'name': 'Presion_MAP', 'value': 100 + random.randint(-10, 10), 'unit': 'kPa'},  
            }

        data = {}
        
        try:
            for pid in self.slow_pids:
                try:
                    self.socket.sendall(f"{pid}\r".encode())
                    time.sleep(0.1)
                    response = self.socket.recv(256).decode('utf-8', errors='ignore')
                    
                    if response:
                        parsed = self.parse_response(response, pid)
                        if parsed and self._validate_pid_value(pid, parsed['value']):
                            data[pid] = parsed

                except Exception as e:
                    print(f"Error leyendo PID {pid}: {e}")
                    continue

            return data

        except Exception as e:
            print(f"Error en read_slow_data: {e}")
            return {}

    def query_pid(self, pid):
        """Consulta un PID específico y retorna el valor decodificado"""
        if not pid or not self.connected:
            return None

        try:
            # Modo emulador: generar datos simulados
            if self._mode == OPERATION_MODES["EMULATOR"]:
                if pid in self.fast_pids:
                    info = self.fast_pids[pid]
                    if pid == '010C':  # RPM
                        value = 800 + random.randint(-50, 50)
                    elif pid == '010D':  # Velocidad
                        value = 60 + random.randint(-5, 5)
                    elif pid == '0105':  # Temp Motor
                        value = 85 + random.randint(-2, 2)
                    elif pid == '0104':  # Carga Motor
                        value = 20 + random.randint(-5, 5)
                    elif pid == '0111':  # Acelerador
                        value = 15 + random.randint(-3, 3)
                    return {
                        'name': info['name'],
                        'value': value,
                        'unit': info['unit']
                    }
                elif pid in self.slow_pids:
                    info = self.slow_pids[pid]
                    if pid == '010F':  # Temp Admision
                        value = 25 + random.randint(-2, 2)
                    elif pid == '012F':  # Combustible
                        value = 75 + random.randint(-5, 5)
                    elif pid == '0142':  # Voltaje
                        value = 12.5 + random.uniform(-0.2, 0.2)
                    elif pid == '010B':  # Presion MAP
                        value = 100 + random.randint(-10, 10)
                    return {
                        'name': info['name'],
                        'value': value,
                        'unit': info['unit']
                    }
                return None

            # Modo WiFi real: consultar dispositivo
            command = f"{pid}\r"
            self.socket.sendall(command.encode())
            
            # Esperar respuesta con timeout
            response = ""
            start_time = time.time()
            while True:
                try:
                    chunk = self.socket.recv(256).decode('utf-8', errors='ignore')
                    response += chunk
                    if '>' in response or time.time() - start_time > 0.2:
                        break
                except socket.timeout:
                    break

            # Parsear respuesta
            parsed = self.parse_response(response, pid)
            if parsed:
                info = (self.fast_pids.get(pid) or 
                       self.slow_pids.get(pid, {}))
                return {
                    'name': info.get('name', 'Unknown'),
                    'value': parsed['value'],
                    'unit': info.get('unit', '')
                }

        except Exception as e:
            print(f"Error consultando PID {pid}: {str(e)}")
            return None

    def query_extended_pid(self, pid, family):
        """Consulta un PID extendido por familia y retorna el valor decodificado"""
        if not pid or not self.connected:
            return None
        try:
            pid_info = self.extended_pid_families.get(family, {}).get(pid)
            if not pid_info:
                return None
            header = pid_info.get('header', '7E0')
            # Comando extendido: enviar encabezado si es necesario
            command = f"{pid}"
            # En ELM327, para encabezado personalizado: AT SH xxx\r

            # Set header
            self._send_command(f"ATSH{header}")
            # Enviar comando PID extendido
            self.socket.sendall((command + '\r').encode())
            response = ""
            start_time = time.time()
            while True:
                try:
                    chunk = self.socket.recv(256).decode('utf-8', errors='ignore')
                    response += chunk
                    if '>' in response or time.time() - start_time > 0.3:
                        break
                except socket.timeout:
                    break
            # Parsear respuesta
            # Buscar bytes de datos (A, B)
            data_bytes = self._extract_data_bytes(response, pid)
            if data_bytes is None:
                return None
            # Decodificar usando la ecuación definida
            eq = pid_info['equation']
            value = None
            if len(data_bytes) == 1:
                value = eq(data_bytes[0])
            elif len(data_bytes) >= 2:
                value = eq(data_bytes[0], data_bytes[1])
            else:
                value = None
            return {
                'name': pid_info['name'],
                'value': round(value, 2) if isinstance(value, float) else value,
                'unit': pid_info['unit']
            }
        except Exception as e:
            print(f"Error consultando PID extendido {pid}: {e}")
            return None

    def _extract_data_bytes(self, response, pid):
        """Extrae los bytes de datos (A, B, ...) de la respuesta OBD para un PID extendido"""
        try:
            # Buscar línea con el PID
            lines = response.replace('\r', '').split('\n')
            for line in lines:
                line = line.strip().replace(' ', '').upper()
                if not line or pid[2:] not in line:
                    continue
                # Buscar después del PID
                idx = line.find(pid[2:])
                if idx == -1:
                    continue
                data = line[idx+len(pid[2:]):]
                # Extraer bytes A, B, ...
                bytes_list = [int(data[i:i+2], 16) for i in range(0, len(data), 2) if len(data[i:i+2])==2]
                return bytes_list
            return None
        except Exception as e:
            print(f"Error extrayendo bytes de respuesta PID {pid}: {e}")
            return None

    def parse_response(self, response, pid):
        """Parsea la respuesta del dispositivo OBD"""
        try:
            # Limpiar respuesta
            lines = response.replace('\r', '').replace('SEARCHING...', '').split('\n')
            lines = [l.strip() for l in lines if l.strip() and 'NO DATA' not in l]
            
            if not lines:
                return None

            # Buscar línea con datos
            for line in lines:
                if len(line) >= 4:
                    # Quitar espacios y convertir a mayúsculas
                    data = line.replace(' ', '').upper()
                    
                    # Validar formato de respuesta
                    if not data.startswith('41'):
                        continue
                        
                    # Extraer bytes de datos
                    data_start = 4  # Saltar "41" + 2 bytes de PID
                    
                    if pid == '010C':  # RPM
                        if len(data) >= data_start + 4:
                            a = int(data[data_start:data_start+2], 16)
                            b = int(data[data_start+2:data_start+4], 16)
                            rpm = ((a * 256) + b) / 4
                            return {'name': 'RPM', 'value': int(rpm), 'unit': 'RPM'}
                            
                    elif pid == '010D':  # Velocidad
                        if len(data) >= data_start + 2:
                            speed = int(data[data_start:data_start+2], 16)
                            return {'name': 'Velocidad', 'value': speed, 'unit': 'km/h'}
                            
                    elif pid == '0105':  # Temperatura motor
                        if len(data) >= data_start + 2:
                            temp = int(data[data_start:data_start+2], 16) - 40
                            return {'name': 'Temp_Motor', 'value': temp, 'unit': '°C'}
                            
                    elif pid == '0104':  # Carga motor
                        if len(data) >= data_start + 2:
                            load = int(data[data_start:data_start+2], 16) * 100.0 / 255.0
                            return {'name': 'Carga_Motor', 'value': round(load, 1), 'unit': '%'}
                            
                    elif pid == '0111':  # Posición acelerador
                        if len(data) >= data_start + 2:
                            throttle = int(data[data_start:data_start+2], 16) * 100.0 / 255.0
                            return {'name': 'Acelerador', 'value': round(throttle, 1), 'unit': '%'}
                            
                    elif pid == '010F':  # Temperatura admisión
                        if len(data) >= data_start + 2:
                            temp = int(data[data_start:data_start+2], 16) - 40
                            return {'name': 'Temp_Admision', 'value': temp, 'unit': '°C'}
                            
                    elif pid == '012F':  # Nivel combustible
                        if len(data) >= data_start + 2:
                            fuel = int(data[data_start:data_start+2], 16) * 100.0 / 255.0
                            return {'name': 'Combustible', 'value': round(fuel, 1), 'unit': '%'}
                            
                    elif pid == '0142':  # Voltaje módulo
                        if len(data) >= data_start + 4:
                            a = int(data[data_start:data_start+2], 16)
                            b = int(data[data_start+2:data_start+4], 16)
                            volt = ((a * 256.0) + b) / 1000.0
                            return {'name': 'Voltaje', 'value': round(volt, 1), 'unit': 'V'}
                            
                    elif pid == '010B':  # Presión MAP
                        if len(data) >= data_start + 2:
                            pressure = int(data[data_start:data_start+2], 16)
                            return {'name': 'Presion_MAP', 'value': pressure, 'unit': 'kPa'}
                            
            return None
            
        except Exception as e:
            print(f"Error parseando respuesta: {str(e)}")
            return None

    def _validate_pid_value(self, pid, value):
        """Valida que los valores estén dentro de rangos realistas"""
        try:
            # Rangos válidos para cada PID
            ranges = {
                '010C': (0, 8000),       # RPM: 0-8000
                '010D': (0, 255),         # Velocidad: 0-255 km/h
                '0105': (-40, 215),       # Temperatura motor: -40 a 215°C
                '0104': (0, 100),         # Carga motor: 0-100%
                '0111': (0, 100),         # Acelerador: 0-100%
                '010F': (-40, 215),       # Temperatura admisión: -40 a 215°C
                '012F': (0, 100),         # Nivel combustible: 0-100%
                '0142': (0, 20),          # Voltaje: 0-20V
                '010B': (0, 255)          # MAP: 0-255 kPa
            }
            
            if pid not in ranges:
                return True
                
            min_val, max_val = ranges[pid]
            return min_val <= value <= max_val
            
        except Exception as e:
            print(f"Error en validación de PID {pid}: {e}")
            return False

class DataLogger:
    """Clase para el registro de datos OBD"""
    
    def __init__(self):
        self.log_dir = "logs"
        self.log_file = None
        self.active = False
        self.logger = logging.getLogger(__name__)
        self._setup_logging()

    def _setup_logging(self):
        """Configura el directorio de logs"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def start_logging(self):
        """Inicia el registro de datos"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(self.log_dir, f"obd_log_{timestamp}.csv")
            
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'PID', 'Name', 'Value', 'Unit'])
            
            self.active = True
            return True
        except Exception as e:
            self.logger.error(f"Error iniciando el logging: {e}")
            return False

    def log_data(self, data):
        """Registra datos en el archivo CSV"""
        if not self.active or not self.log_file:
            return False
            
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                for pid, info in data.items():
                    writer.writerow([
                        timestamp,
                        pid,
                        info['name'],
                        info['value'],
                        info['unit']
                    ])
            return True
        except Exception as e:
            self.logger.error(f"Error registrando datos: {e}")
            return False

    def log_pid_selection(self, fast_pids, slow_pids, extended_pids):
        """Registra el estado de selección de los PIDs (checkboxes) en el log para trazabilidad"""
        if not self.active or not self.log_file:
            return False
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                writer.writerow([timestamp, 'PID_SELECTION', 'FAST', str(fast_pids), ''])
                writer.writerow([timestamp, 'PID_SELECTION', 'SLOW', str(slow_pids), ''])
                for fam, fam_pids in extended_pids.items():
                    writer.writerow([timestamp, f'PID_SELECTION_EXT_{fam}', fam, str(fam_pids), ''])
            return True
        except Exception as e:
            self.logger.error(f"Error registrando selección de PIDs: {e}")
            return False

    def get_status(self):
        """Obtiene el estado actual del logger"""
        try:
            if not self.active or not self.log_file:
                return {'active': False}

            size_bytes = os.path.getsize(self.log_file)
            size_mb = size_bytes / (1024 * 1024)
            
            return {
                'active': self.active,
                'file': self.log_file,
                'size': f"{size_mb:.2f}MB"
            }
        except Exception as e:
            self.logger.error(f"Error obteniendo estado del logger: {e}")
            return {'active': False}

class HighSpeedOBDDashboard(QMainWindow):
    """Dashboard principal para OBD de alta velocidad"""
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.slow_timer = QTimer()
        self.elm327 = OptimizedELM327Connection()
        self.logger = DataLogger()
        self.setup_ui()
        self.connect_signals()
        self.last_update = time.time()
        self.actual_speed = 0
        
    def setup_ui(self):
        """Configura la interfaz de usuario con pestañas: Selección de PIDs y Visualización de Datos"""
        self.setWindowTitle("🚗 Dashboard OBD-II Optimizado")
        self.setMinimumSize(1000, 700)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Estado del sistema
        status_box = QGroupBox("⚡ Estado")
        status_layout = QHBoxLayout(status_box)
        self.connection_status = QLabel("🔴 DESCONECTADO")
        self.connection_status.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.speed_status = QLabel("⚡ Velocidad: -- Hz")
        self.speed_status.setStyleSheet("font-size: 16px;")
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.speed_status)
        status_layout.addStretch()
        main_layout.addWidget(status_box)

        # Panel de control
        control_box = QGroupBox("🎮 Control")
        control_layout = QHBoxLayout(control_box)
        control_layout.setSpacing(10)
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Modo:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["WiFi", "Emulador"])
        self.mode_combo.setStyleSheet("font-size: 14px;")
        mode_layout.addWidget(self.mode_combo)
        control_layout.addLayout(mode_layout)
        self.connect_btn = QPushButton("🔌 Conectar")
        self.start_fast_btn = QPushButton("⚡ Modo Rápido (5Hz)")
        self.start_normal_btn = QPushButton("🚗 Normal (2Hz)")
        self.stop_btn = QPushButton("⏹️ Detener")
        for btn in [self.connect_btn, self.start_fast_btn, self.start_normal_btn, self.stop_btn]:
            btn.setStyleSheet("font-size: 14px; padding: 8px 16px; background: #007BFF; color: white; border: none; border-radius: 4px;")
            control_layout.addWidget(btn)
        control_layout.addStretch()
        main_layout.addWidget(control_box)

        # --- NUEVO: Tabs ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, stretch=1)

        # Tab 1: Selección de PIDs
        pid_tab = QWidget()
        pid_layout = QVBoxLayout(pid_tab)
        self.pid_selection = PIDCheckboxPanel("Principal", self.elm327.fast_pids)
        self.slow_pid_selection = PIDCheckboxPanel("Secundario", self.elm327.slow_pids)
        self.apply_pid_btn = QPushButton("✅ Aplicar")
        pid_layout.addWidget(self.pid_selection)
        pid_layout.addWidget(self.slow_pid_selection)
        # Paneles extendidos
        self.extended_pid_panels = {}
        for fam, fam_pids in self.elm327.extended_pid_families.items():
            panel = PIDCheckboxPanel(fam, fam_pids)
            self.extended_pid_panels[fam] = panel
            pid_layout.addWidget(panel)
        pid_layout.addWidget(self.apply_pid_btn)
        self.tabs.addTab(pid_tab, "Selección de PIDs")

        # Tab 2: Visualización de Datos
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_box = QGroupBox("📊 Datos en Tiempo Real")
        grid = QGridLayout(data_box)
        # Panel principal
        fast_widget = QWidget()
        fast_layout = QGridLayout(fast_widget)
        row = 0
        self.pid_labels = {}
        for pid, info in self.elm327.fast_pids.items():
            name_label = QLabel(f"{info['name']}:")
            value_label = QLabel("--")
            unit_label = QLabel(info['unit'])
            fast_layout.addWidget(name_label, row, 0)
            fast_layout.addWidget(value_label, row, 1)
            fast_layout.addWidget(unit_label, row, 2)
            self.pid_labels[pid] = value_label
            row += 1
        grid.addWidget(fast_widget, 0, 0)
        # Panel secundario
        slow_widget = QWidget()
        slow_layout = QGridLayout(slow_widget)
        row = 0
        self.slow_pid_labels = {}
        for pid, info in self.elm327.slow_pids.items():
            name_label = QLabel(f"{info['name']}:")
            value_label = QLabel("--")
            unit_label = QLabel(info['unit'])
            slow_layout.addWidget(name_label, row, 0)
            slow_layout.addWidget(value_label, row, 1)
            slow_layout.addWidget(unit_label, row, 2)
            self.slow_pid_labels[pid] = value_label
            row += 1
        grid.addWidget(slow_widget, 0, 1)
        data_layout.addWidget(data_box)
        self.tabs.addTab(data_tab, "Visualización de Datos")

    def connect_signals(self):
        """Conecta las señales de los widgets"""
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.start_fast_btn.clicked.connect(lambda: self.start_reading(5))
        self.start_normal_btn.clicked.connect(lambda: self.start_reading(2))
        self.stop_btn.clicked.connect(self.stop_reading)
        self.apply_pid_btn.clicked.connect(self.apply_pid_selection)
        self.timer.timeout.connect(self.read_fast_data)
        self.slow_timer.timeout.connect(self.read_slow_data)

    def toggle_connection(self):
        """Alterna la conexión con el dispositivo"""
        try:
            if not self.elm327.connected:
                is_emulator = self.mode_combo.currentText() == "Emulador"
                self.elm327._mode = (OPERATION_MODES["EMULATOR"]
                                   if is_emulator
                                   else OPERATION_MODES["WIFI"])
                
                if not is_emulator:
                    self.elm327.ip = "192.168.0.10"
                    
                if self.elm327.connect():
                    self.connection_status.setText(
                        "🟢 CONECTADO - " +
                        ("Emulador" if is_emulator else "WiFi")
                    )
                    self.connect_btn.setText("🔌 Desconectar")
                else:
                    self.connection_status.setText("🔴 ERROR")
            else:
                self.stop_reading()
                self.elm327.disconnect()
                self.connection_status.setText("🔴 DESCONECTADO")
                self.connect_btn.setText("🔌 Conectar")
                
        except Exception as e:
            print(f"Error de conexión: {e}")
            self.connection_status.setText("🔴 ERROR")

    def start_reading(self, speed):
        """Inicia la lectura de datos"""
        if not self.elm327.connected:
            return
            
        self.stop_reading()
        self.actual_speed = speed
        interval = int(1000 / speed)  # Convertir Hz a ms
        self.timer.start(interval)
        self.slow_timer.start(1000)  # 1Hz para datos secundarios
        self.speed_status.setText(f"⚡ Velocidad: {speed} Hz")
        
        if not self.logger.active:
            self.logger.start_logging()

    def stop_reading(self):
        """Detiene la lectura de datos"""
        self.timer.stop()
        self.slow_timer.stop()
        self.actual_speed = 0
        self.speed_status.setText("⚡ Velocidad: -- Hz")
        
    def apply_pid_selection(self):
        """Aplica la selección de PIDs y la registra en el log"""
        selected_fast = self.pid_selection.get_selected_pids()
        selected_slow = self.slow_pid_selection.get_selected_pids()
        self.selected_extended_pids = {}
        for fam, panel in self.extended_pid_panels.items():
            self.selected_extended_pids[fam] = panel.get_selected_pids()
        if not selected_fast and not selected_slow and not any(self.selected_extended_pids.values()):
            return
        # Resetear los valores
        for pid in self.pid_labels:
            self.pid_labels[pid].setText("--")
        for pid in self.slow_pid_labels:
            self.slow_pid_labels[pid].setText("--")
        # Registrar selección de PIDs
        if not self.logger.active:
            self.logger.start_logging()
        self.logger.log_pid_selection(selected_fast, selected_slow, self.selected_extended_pids)

    def read_fast_data(self):
        """Lee y actualiza solo el dato de RPM en la interfaz para máxima fluidez"""
        if not self.elm327.connected:
            return
        rpm_pid = '010C'
        rpm_info = self.elm327.query_pid(rpm_pid)
        if rpm_info and self.elm327._validate_pid_value(rpm_pid, rpm_info['value']):
            if rpm_pid in self.pid_labels:
                self.pid_labels[rpm_pid].setText(str(rpm_info['value']))
            if hasattr(self.logger, 'active') and self.logger.active:
                self.logger.log_data({rpm_pid: rpm_info})
        # Otros PIDs se pueden actualizar en el timer lento

    def read_slow_data(self):
        """Lee y actualiza los datos lentos en la interfaz"""
        if not self.elm327.connected:
            return
        data = self.elm327.read_slow_data()
        if data:
            for pid, info in data.items():
                if pid in self.slow_pid_labels:
                    self.slow_pid_labels[pid].setText(str(info['value']))
            self.logger.log_data(data)
        # --- Leer y mostrar PIDs extendidos seleccionados ---
        if hasattr(self, 'selected_extended_pids'):
            for fam, pid_list in self.selected_extended_pids.items():
                for pid in pid_list:
                    info = self.elm327.query_extended_pid(pid, fam)
                    # No mostrar en la UI, pero sí loggear si se desea
                    if info and hasattr(self.logger, 'active') and self.logger.active:
                        self.logger.log_data({pid: info})
        
def main():
    """Función principal de la aplicación"""
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
