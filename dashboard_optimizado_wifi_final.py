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
import json
from datetime import datetime
from PyQt6.QtMultimedia import QSoundEffect

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QGridLayout, QComboBox,
    QCheckBox, QScrollArea, QTabWidget, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QAction

from data_logger import DataLogger

import threading
import queue

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
    """
    Panel de checkboxes para selección de PIDs.
    Permite seleccionar dinámicamente los parámetros a monitorear.
    """
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
    """
    Clase para manejar la conexión con el dispositivo ELM327.
    Soporta modo emulador y real, y carga dinámica de bibliotecas de PIDs.
    """
    
    def __init__(self):
        # PIDs extendidos SOLO Toyota Hilux (no Jeep, no Chrysler)
        self.extended_pids = {
            # Modo 01 (estándar y extendidos)
            '0105': {'name': 'Engine coolant temperature', 'unit': '°C'},
            '010C': {'name': 'Engine RPM', 'unit': 'rpm'},
            '010D': {'name': 'Vehicle speed', 'unit': 'km/h'},
            '012F': {'name': 'Fuel level input', 'unit': '%'},
            '0133': {'name': 'Barometric pressure', 'unit': 'kPa'},
            '0146': {'name': 'Ambient air temperature', 'unit': '°C'},
            '015C': {'name': 'Engine oil temperature', 'unit': '°C'},
            '0161': {'name': 'Driver demand torque', 'unit': '%'},
            '0162': {'name': 'Actual engine torque', 'unit': '%'},
            '0163': {'name': 'Engine reference torque', 'unit': 'Nm'},
            '017C': {'name': 'DPF temperature', 'unit': '°C'},
            # Modo 21/22 extendidos Hilux
            '21B2': {'name': 'Ignition knock retard', 'unit': '°'},
            '21D9': {'name': 'ATF temperature', 'unit': '°C'},
            '21A3': {'name': 'DPF differential pressure', 'unit': 'kPa'},
            '21DA': {'name': 'Current gear', 'unit': 'gear'},
            '221627': {'name': 'ATF pressure stage 2', 'unit': 'kPa'},
            # Otros extendidos útiles
            '2133': {'name': 'Barometric pressure (ext)', 'unit': 'kPa'},
            '2146': {'name': 'Ambient air temp (ext)', 'unit': '°C'},
            '220B2': {'name': 'Ignition knock retard (ext)', 'unit': '°'},
            # Puedes agregar más según tu CSV o necesidades
        }
        self.extended_parsers = {
            '0105': lambda raw: int(raw[0:2],16)-40 if len(raw)>=2 else None,
            '010C': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16))/4 if len(raw)>=4 else None,
            '010D': lambda raw: int(raw[0:2],16) if len(raw)>=2 else None,
            '012F': lambda raw: int(raw[0:2],16)*100/255 if len(raw)>=2 else None,
            '0133': lambda raw: int(raw[0:2],16) if len(raw)>=2 else None,
            '0146': lambda raw: int(raw[0:2],16)-40 if len(raw)>=2 else None,
            '015C': lambda raw: int(raw[0:2],16)-40 if len(raw)>=2 else None,
            '0161': lambda raw: int(raw[0:2],16)-125 if len(raw)>=2 else None,
            '0162': lambda raw: int(raw[0:2],16)-125 if len(raw)>=2 else None,
            '0163': lambda raw: int(raw[0:2],16)*256+int(raw[2:4],16) if len(raw)>=4 else None,
            '017C': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16))/10-40 if len(raw)>=4 else None,
            '21B2': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16))/32-64 if len(raw)>=4 else None,
            '21D9': lambda raw: int(raw[0:2],16)-40 if len(raw)>=2 else None,
            '21A3': lambda raw: int(raw[0:2],16)*256+int(raw[2:4],16) if len(raw)>=4 else None,
            '21DA': lambda raw: int(raw[0:2],16) if len(raw)>=2 else None,
            '221627': lambda raw: int(raw[0:2],16)*256+int(raw[2:4],16) if len(raw)>=4 else None,
            '2133': lambda raw: int(raw[0:2],16) if len(raw)>=2 else None,
            '2146': lambda raw: int(raw[0:2],16)-40 if len(raw)>=2 else None,
            '220B2': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16))/32-64 if len(raw)>=4 else None,
        }
        # Inicializar extended_parsers como diccionario vacío
        self.extended_parsers = {}
        self._mode = OPERATION_MODES["WIFI"]
        self.ip = "192.168.0.10"
        self.port = 35000
        # PIDs rápidos y lentos como diccionarios vacíos
        self.fast_pids = {}
        self.slow_pids = {}
        # PIDs extendidos Jeep Grand Cherokee (solo Jeep)
        self.extended_pids_jeep = {
            '221910': {'name': 'Trans Fluid Temp', 'unit': 'C'},
            '221136': {'name': 'Engine Oil Temp', 'unit': 'C'},
            '22111C': {'name': 'Oil Pressure', 'unit': 'kPa'},
            '221134': {'name': 'Battery Voltage', 'unit': 'V'},
            '2220CB': {'name': 'Knock Retard', 'unit': '°'},
            '220298': {'name': 'Injector PW1', 'unit': 'us'},
            '22029A': {'name': 'Injector PW2', 'unit': 'us'},
            '22029C': {'name': 'Injector PW3', 'unit': 'us'},
            '22029E': {'name': 'Injector PW4', 'unit': 'us'},
            '2202A0': {'name': 'Injector PW5', 'unit': 'us'},
            '2202A2': {'name': 'Injector PW6', 'unit': 'us'},
            '2202A4': {'name': 'Injector PW7', 'unit': 'us'},
            '2202A6': {'name': 'Injector PW8', 'unit': 'us'},
            '221A00': {'name': 'Trans Output Shaft Speed', 'unit': 'rpm'},
            '221A02': {'name': 'Trans Input Shaft Speed', 'unit': 'rpm'},
            '221A08': {'name': 'Trans Torque Converter Slip', 'unit': 'rpm'},
            '22201D': {'name': 'Engine Torque', 'unit': 'Nm'},
            '22191A': {'name': 'Trans Fluid Pressure', 'unit': 'bar'},
            '221138': {'name': 'Oil Life Remaining', 'unit': '%'},
            '221A18': {'name': 'Gearbox Selected Gear', 'unit': 'N'},
            '22190E': {'name': 'Transmission Fluid Level', 'unit': 'L'},
            '221A10': {'name': 'Transfer Case Oil Temp', 'unit': 'C'},
            '22110A': {'name': 'Differential Oil Temp', 'unit': 'C'},
            '224901': {'name': 'ABS Wheel Speed FL', 'unit': 'km/h'},
            '224903': {'name': 'ABS Wheel Speed FR', 'unit': 'km/h'},
            '224905': {'name': 'ABS Wheel Speed RL', 'unit': 'km/h'},
            '224907': {'name': 'ABS Wheel Speed RR', 'unit': 'km/h'},
            '2216BC': {'name': 'Steering Angle', 'unit': 'deg'},
            '2216A2': {'name': 'G-Force Lateral', 'unit': 'g'},
            '2216A0': {'name': 'G-Force Longitudinal', 'unit': 'g'},
            '2216A4': {'name': 'Yaw Rate', 'unit': 'deg/s'},
            '22120B': {'name': 'Barometric Pressure', 'unit': 'kPa'},
            '221202': {'name': 'Manifold Absolute Pressure', 'unit': 'bar'}
        }
        self.extended_parsers_jeep = {
            '221910': lambda raw: int(raw[0:2], 16) - 40 if len(raw) >= 2 else None,
            '221136': lambda raw: int(raw[0:2], 16) - 40 if len(raw) >= 2 else None,
            '22111C': lambda raw: int(raw[0:2], 16) * 4 if len(raw) >= 2 else None,
            '221134': lambda raw: int(raw[0:2], 16) / 10 if len(raw) >= 2 else None,
            '2220CB': lambda raw: (((int(raw[0:2],16)<<8)+int(raw[2:4],16))*0.05) if len(raw)>=4 else None,
            '220298': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '22029A': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '22029C': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '22029E': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '2202A0': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '2202A2': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '2202A4': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '2202A6': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '221A00': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '221A02': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '221A08': lambda raw: (int(raw[0:2],16)*256+int(raw[2:4],16)) if len(raw)>=4 else None,
            '22201D': lambda raw: ((int(raw[0:2],16)*256+int(raw[2:4],16))/8) if len(raw)>=4 else None,
            '22191A': lambda raw: ((int(raw[0:2],16)*256+int(raw[2:4],16))/100) if len(raw)>=4 else None,
            '221138': lambda raw: int(raw[0:2],16) if len(raw)>=2 else None,
            '221A18': lambda raw: int(raw[0:2],16) if len(raw)>=2 else None,
            '22190E': lambda raw: ((int(raw[0:2],16)*256+int(raw[2:4],16))/100) if len(raw)>=4 else None,
            '221A10': lambda raw: int(raw[0:2],16)-40 if len(raw)>=2 else None,
            '22110A': lambda raw: int(raw[0:2],16)-40 if len(raw)>=2 else None,
            '224901': lambda raw: ((int(raw[0:2],16)*256+int(raw[2:4],16))/100) if len(raw)>=4 else None,
            '224903': lambda raw: ((int(raw[0:2],16)*256+int(raw[2:4],16))/100) if len(raw)>=4 else None,
            '224905': lambda raw: ((int(raw[0:2],16)*256+int(raw[2:4],16))/100) if len(raw)>=4 else None,
            '224907': lambda raw: ((int(raw[0:2],16)*256+int(raw[2:4],16))/100) if len(raw)>=4 else None,
            '2216BC': lambda raw: ((int(raw[0:2],16)*256+int(raw[2:4],16))/10-720) if len(raw)>=4 else None,
            '2216A2': lambda raw: (((int(raw[0:2],16)*256+int(raw[2:4],16))-20000)/1000) if len(raw)>=4 else None,
            '2216A0': lambda raw: (((int(raw[0:2],16)*256+int(raw[2:4],16))-20000)/1000) if len(raw)>=4 else None,
            '2216A4': lambda raw: (((int(raw[0:2],16)*256+int(raw[2:4],16))-20000)/100) if len(raw)>=4 else None,
            '22120B': lambda raw: int(raw[0:2],16) if len(raw)>=2 else None,
            '221202': lambda raw: ((int(raw[0:2],16)*256+int(raw[2:4],16))/100) if len(raw)>=4 else None
        }
        # Inicializar extended_parsers como diccionario vacío
        self.extended_parsers = {}
        self._mode = OPERATION_MODES["WIFI"]
        self.ip = "192.168.0.10"
        self.port = 35000
        # PIDs rápidos y lentos como diccionarios vacíos
        self.fast_pids = {}
        self.slow_pids = {}
    logger = logging.getLogger(__name__)

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
        if not self.connected or self.socket is None:
            self.logger.error("No hay conexión activa con el ELM327.")
            return None
            
        if self._mode == OPERATION_MODES["EMULATOR"]:
            return self._emulate_response(cmd)
            
        try:
            cmd = cmd.encode() + b'\r\n'
            try:
                self.socket.sendall(cmd)
            except Exception as e:
                self.logger.error(f"Error enviando comando (socket): {e}")
                self.disconnect()
                return None
            
            response = ""
            start_time = time.time()
            
            while '>' not in response:
                try:
                    chunk = self.socket.recv(256).decode('utf-8', errors='ignore')
                    response += chunk
                    if time.time() - start_time > 0.5:
                        break
                except (socket.timeout, OSError) as e:
                    self.logger.error(f"Timeout/OS error recibiendo respuesta: {e}")
                    break
                except Exception as e:
                    self.logger.error(f"Error recibiendo respuesta: {e}")
                    break
                    
            return response
        except Exception as e:
            self.logger.error(f"Error general enviando comando: {e}")
            self.disconnect()
            return None

    def _emulate_response(self, cmd):
        """Emula respuestas del dispositivo para pruebas, incluyendo DTCs simulados"""
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
            '010B': lambda: f"410B{random.randint(0, 255):02X}",
            # Simulación de DTCs: 2 códigos (P0133 y U0100)
            '03': lambda: "43 02 01 33 10 00 \r\r>",
            '04': lambda: "44 \r\r>"
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

    def query_pid(self, pid):
        """Consulta un PID específico y retorna el valor decodificado (soporta extendidos modo 22)"""
        if not pid or not self.connected or self.socket is None:
            return None
        try:
            # --- Modo emulador: datos simulados ---
            if self._mode == OPERATION_MODES["EMULATOR"]:
                if pid in self.fast_pids:
                    info = self.fast_pids[pid]
                    value = random.randint(700, 800) if pid == '010C' else random.randint(10, 100)
                    return {'name': info['name'], 'value': value, 'unit': info['unit']}
                elif pid in self.slow_pids:
                    info = self.slow_pids[pid]
                    value = random.randint(20, 80)
                    return {'name': info['name'], 'value': value, 'unit': info['unit']}
                elif pid in self.extended_pids:
                    info = self.extended_pids[pid]
                    value = random.randint(10, 100)
                    return {'name': info['name'], 'value': value, 'unit': info['unit']}
                return None

            # --- Modo real: ---
            if pid in self.fast_pids or pid in self.slow_pids:
                command = f"{pid}\r\n"
            elif pid in self.extended_pids:
                command = f"22{pid[2:]}\r\n"
            else:
                return None
            try:
                self.socket.sendall(command.encode())
                print(f"[DEBUG] Enviado PID: {command.strip()}")
            except Exception as e:
                self.logger.error(f"Error enviando comando {pid}: {e}")
                return None
            response = ""
            start_time = time.time()
            while True:
                try:
                    chunk = self.socket.recv(256).decode('utf-8', errors='ignore')
                    response += chunk
                    if '>' in response or time.time() - start_time > 0.5:
                        break
                except socket.timeout:
                    break
                except Exception as e:
                    self.logger.error(f"Error recibiendo respuesta para {pid}: {e}")
                    break
            print(f"[DEBUG] Respuesta cruda PID {pid}: {repr(response)}")
            # --- Parseo ---
            if pid in self.fast_pids or pid in self.slow_pids:
                parsed = self.parse_response(response, pid)
                if parsed:
                    info = (self.fast_pids.get(pid) or self.slow_pids.get(pid, {}))
                    return {'name': info.get('name', 'Unknown'), 'value': parsed['value'], 'unit': info.get('unit', '')}
            elif pid in self.extended_pids:
                lines = response.replace('\r', '').replace('>', '').split('\n')
                lines = [l.strip() for l in lines if l.strip() and 'NO DATA' not in l]
                for line in lines:
                    data = line.replace(' ', '').upper()
                    if data.startswith('62') and len(data) > 6:
                        raw = data[6:]
                        value = None
                        # Intentar parseo personalizado
                        parser = self.extended_parsers.get(pid)
                        if parser:
                            try:
                                value = parser(raw)
                            except Exception as e:
                                print(f"[ADVERTENCIA] Error parseando PID extendido {pid}: {e}")
                                value = None
                        if value is None:
                            print(f"[ADVERTENCIA] Valor no parseado para PID extendido {pid}, valor crudo: {raw}")
                            value = raw
                        info = self.extended_pids[pid]
                        print(f"[DEBUG] Parseo EXT {pid}: {raw} -> {value}")
                        return {'name': info['name'], 'value': value, 'unit': info['unit']}
                print(f"[ADVERTENCIA] No se encontró respuesta válida para PID extendido {pid}. Respuesta: {response}")
                return {'name': self.extended_pids[pid]['name'], 'value': 'Sin datos', 'unit': self.extended_pids[pid]['unit']}
        except Exception as e:
            self.logger.error(f"Error consultando PID {pid}: {str(e)}")
            return None

    def parse_response(self, response, pid):
        """Parsea la respuesta del dispositivo OBD (mejorado para respuestas multilínea y eco)"""
        try:
            # Limpiar respuesta
            lines = response.replace('\r', '').replace('SEARCHING...', '').split('\n')
            lines = [l.strip() for l in lines if l.strip() and 'NO DATA' not in l]
            if not lines:
                return None
            # Buscar la última línea válida que empiece con '41' y el PID correcto
            pid_short = pid[2:]
            for line in reversed(lines):
                data = line.replace(' ', '').upper()
                if data.startswith('41' + pid_short):
                    data_start = 4  # Saltar '41' + 2 bytes de PID
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
                            volt = ((a * 256.0) + b) / 1000
                            return {'name': 'Voltaje', 'value': round(volt, 1), 'unit': 'V'}
                    elif pid == '010B':  # Presión MAP
                        if len(data) >= data_start + 2:
                            pressure = int(data[data_start:data_start+2], 16)
                            return {'name': 'Presion_MAP', 'value': pressure, 'unit': 'kPa'}
            return None
        except Exception as e:
            print(f"Error parseando respuesta: {str(e)}")
            return None

    def read_dtc(self):
        """Lee códigos DTC almacenados usando comando OBD-II estándar (robusto para frames múltiples y byte de cantidad atípico, soporta respuestas como '43 01 01 13', muestra siempre la línea cruda y hex, y extrae todos los DTCs posibles)"""
        try:
            if not self.connected:
                return ["[ERROR] No conectado"]
            self._send_command('AT D')  # Limpia buffer
            print("[DEBUG] Enviado DTC: 03")
            resp = self._send_command('03')
            print(f"[DEBUG] Respuesta cruda DTC: {repr(resp)}")
            if not resp:
                return ["[ERROR] Sin respuesta"]
            dtcs = []
            raw_codes = []
            lines = resp.replace('\r', '').split('\n')
            for line in lines:
                line = line.strip().replace(' ', '')
                if not line or not line.startswith('43'):
                    continue
                print(f"[DEBUG] Línea relevante DTC: {line}")
                # Log hexadecimal byte a byte
                hex_bytes = [line[i:i+2] for i in range(0, len(line), 2)]
                if hex_bytes:
                    print(f"[DEBUG] Línea relevante HEX: {' '.join(hex_bytes)}")
                    dtcs.append(f"HEX: {' '.join(hex_bytes)}")
                else:
                    print(f"[DEBUG] Línea relevante HEX: (no convertible)")
                dtcs.append(f"RAW: {line}")
                # Extraer todos los códigos posibles de 4 en 4 caracteres a partir del tercer byte (saltando '43' + byte de cantidad = 4 chars)
                data = line[4:]  # Saltar '43' + byte de cantidad (2 bytes = 4 chars)
                # El byte de cantidad indica la cantidad de DTCs, pero algunos ECUs pueden no respetarlo
                for i in range(0, len(data), 4):
                    code = data[i:i+4]
                    if code and code != '0000' and len(code) == 4:
                        raw_codes.append(code)
                        dtc_fmt = self._format_dtc(code)
                        dtcs.append(dtc_fmt if dtc_fmt else code)
            print(f"[DEBUG] Códigos DTC crudos extraídos: {raw_codes}")
            print(f"[DEBUG] Códigos DTC formateados: {dtcs}")
            if not raw_codes:
                dtcs.append("[INFO] No se encontraron DTCs activos (respuesta válida pero sin códigos)")
            self._send_command('AT D')
            return dtcs
        except Exception as e:
            self.logger.error(f"Error leyendo DTC: {e}")
            return [f"[ERROR] {e}"]

    def clear_dtc(self):
        """Borra códigos DTC almacenados usando comando OBD-II estándar"""
        try:
            if not self.connected:
                return False
            self._send_command('AT D')
            print("[DEBUG] Enviado CLEAR DTC: 04")
            resp = self._send_command('04')
            print(f"[DEBUG] Respuesta cruda CLEAR DTC: {repr(resp)}")
            # Flush extra para limpiar el buffer tras borrar DTC
            self._send_command('AT D')
            time.sleep(0.2)
            return resp and ('OK' in resp or '44' in resp)
        except Exception as e:
            self.logger.error(f"Error borrando DTC: {e}")
            return False

    def _format_dtc(self, code):
        """Formatea un código DTC hexadecimal a estándar OBD-II"""
        if len(code) != 4:
            return code
        first = int(code[0], 16)
        dtc_type = ['P', 'C', 'B', 'U'][first >> 2]
        dtc = dtc_type + format((first & 0x3), 'X') + code[1:]
        return dtc

    def validate_pid_value(self, pid, value):
        """Valida que los valores estén dentro de rangos realistas (método público)"""
        try:
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

    def detect_protocol(self):
        """Detecta el protocolo OBD-II utilizado por la ECU y lo muestra en la UI/log."""
        if not self.connected:
            return None
        # Enviar comando ATDP para detectar protocolo
        try:
            resp = self._send_command('ATDP')
            if resp:
                # Buscar línea relevante
                lines = resp.replace('\r', '').replace('>', '').split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('ATDP') and 'OK' not in line:
                        print(f"[INFO] Protocolo detectado: {line}")
                        return line
            return None
        except Exception as e:
            print(f"[ERROR] Error detectando protocolo: {e}")
            return None

    def load_pid_library(self, protocol=None):
        """Carga la biblioteca de PIDs desde archivos CSV según el protocolo detectado."""
        import_path = os.path.join(os.path.dirname(__file__), 'pids')
        # Cargar universal (si existe)
        universal_csv = os.path.join(import_path, 'universal_standard.csv')
        if os.path.exists(universal_csv):
            try:
                with open(universal_csv, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fast, slow = {}, {}
                    for row in reader:
                        pid = row.get('PID', '').strip().upper()
                        name = row.get('Name', '').strip()
                        unit = row.get('Unit', '').strip()
                        tipo = row.get('Type', '').strip().lower()  # 'fast' o 'slow'
                        if not pid or not name:
                            continue
                        entry = {'name': name, 'unit': unit}
                        if tipo == 'fast':
                            fast[pid] = entry
                        elif tipo == 'slow':
                            slow[pid] = entry
                    if fast:
                        self.fast_pids = fast
                    if slow:
                        self.slow_pids = slow
                print(f"[INFO] Biblioteca universal de PIDs cargada: {len(self.fast_pids)} fast, {len(self.slow_pids)} slow")
            except Exception as e:
                print(f"[ERROR] Error cargando universal_standard.csv: {e}")
        else:
            print("[INFO] No se encontró universal_standard.csv, usando PIDs por defecto.")
        # Cargar extendidos según protocolo
        if protocol:
            proto_key = protocol.lower().replace('/', '_').replace(' ', '_')
            ext_csv = os.path.join(import_path, f'extended_{proto_key}.csv')
            if os.path.exists(ext_csv):
                try:
                    with open(ext_csv, newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        ext = {}
                        for row in reader:
                            pid = row.get('PID', '').strip().upper()
                            name = row.get('Name', '').strip()
                            unit = row.get('Unit', '').strip()
                            if not pid or not name:
                                continue
                            ext[pid] = {'name': name, 'unit': unit}
                        if ext:
                            self.extended_pids = ext
                    print(f"[INFO] Biblioteca extendida de PIDs cargada: {len(self.extended_pids)} para {protocol}")
                except Exception as e:
                    print(f"[ERROR] Error cargando extended_{proto_key}.csv: {e}")
            else:
                print(f"[INFO] No se encontró extended_{proto_key}.csv, usando PIDs extendidos por defecto.")

    def set_vehicle_mode(self, vehicle_name):
        """Configura los PIDs extendidos y parsers según el vehículo seleccionado"""
        if vehicle_name == "Jeep Grand Cherokee":
            self.extended_pids = self.extended_pids_jeep
            self.extended_parsers = self.extended_parsers_jeep
        else:
            # Toyota Hilux u otro
            # Deja los defaults ya cargados en self.extended_pids y self.extended_parsers
            pass

class AlertManager:
    """
    Gestor de alertas visuales y sonoras según configuración y umbrales.
    Lee la configuración desde dashboard_config.json.
    """
    def __init__(self, config):
        self.thresholds = config.get('pid_thresholds', {})
        self.visual_enabled = config.get('alert', {}).get('visual', True)
        self.sound_enabled = config.get('alert', {}).get('sound', True)
        self.sound_effect = None
        if self.sound_enabled:
            self.sound_effect = QSoundEffect()
            self.sound_effect.setSource(QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), 'alert.wav')))
            self.sound_effect.setVolume(0.7)

    def check_and_alert(self, pid, value, label_widget=None):
        """Verifica si el valor está fuera de umbral y lanza alerta visual/sonora."""
        th = self.thresholds.get(pid)
        if th is None or value is None:
            return
        min_v, max_v = th.get('min'), th.get('max')
        if (min_v is not None and value < min_v) or (max_v is not None and value > max_v):
            if self.visual_enabled and label_widget is not None:
                label_widget.setStyleSheet('background-color: #ff5252; color: white; font-weight: bold;')
            if self.sound_enabled and self.sound_effect:
                self.sound_effect.play()
        else:
            if label_widget is not None:
                label_widget.setStyleSheet('')

class StartupModeDialog(QDialog):
    """
    Diálogo de selección de modo inicial (auto, genérico, vehículo).
    Permite elegir el perfil de vehículo y el modo de conexión.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar modo de inicio")
        self.setModal(True)
        layout = QVBoxLayout(self)
        self.selected_mode = None
        self.selected_vehicle = None
        label = QLabel("¿Cómo deseas iniciar el dashboard?")
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(label)
        # Botones de modo
        self.auto_btn = QPushButton("🔍 Selección automática (recomendado)")
        self.generic_btn = QPushButton("⚙️ Modo genérico OBD-II")
        self.vehicle_btn = QPushButton("🚗 Selección de vehículo específico")
        layout.addWidget(self.auto_btn)
        layout.addWidget(self.generic_btn)
        layout.addWidget(self.vehicle_btn)
        # Combo de vehículos (solo visible si se elige selección de vehículo)
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.addItems(["Toyota Hilux", "Jeep Grand Cherokee", "Otro (próximamente)"])
        self.vehicle_combo.setVisible(False)
        layout.addWidget(self.vehicle_combo)
        # Botones aceptar/cancelar
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.button_box)
        self.auto_btn.clicked.connect(self.select_auto)
        self.generic_btn.clicked.connect(self.select_generic)
        self.vehicle_btn.clicked.connect(self.select_vehicle)
        self.vehicle_combo.currentIndexChanged.connect(self.vehicle_selected)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        # Deshabilitar OK al inicio
        ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setEnabled(False)
        self.ok_btn = ok_btn
    def select_auto(self):
        self.selected_mode = 'auto'
        self.vehicle_combo.setVisible(False)
        if self.ok_btn:
            self.ok_btn.setEnabled(True)
    def select_generic(self):
        self.selected_mode = 'generic'
        self.vehicle_combo.setVisible(False)
        if self.ok_btn:
            self.ok_btn.setEnabled(True)
    def select_vehicle(self):
        self.selected_mode = 'vehicle'
        self.vehicle_combo.setVisible(True)
        if self.ok_btn:
            self.ok_btn.setEnabled(True)
    def vehicle_selected(self, idx):
        self.selected_vehicle = self.vehicle_combo.currentText()

class HighSpeedOBDDashboard(QMainWindow):
    """
    Dashboard principal para OBD de alta velocidad.
    Gestiona la UI, la lógica de adquisición, alertas y logging.
    """
    
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.slow_timer = QTimer()
        self.elm327 = OptimizedELM327Connection()
        self.logger = DataLogger()
        self.selected_fast_pids = []
        self.selected_slow_pids = []
        self.selected_extended_pids = []
        self.startup_mode = None
        self.selected_vehicle = None
        self.data_queue = queue.Queue(maxsize=10)
        self.reader_thread = None
        self.reader_thread_stop = threading.Event()
        # Cargar configuración
        config_path = os.path.join(os.path.dirname(__file__), 'dashboard_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.alert_manager = AlertManager(self.config)
        # Activar logging en SQLite si está configurado
        if self.config.get('logging', {}).get('sqlite', False):
            self.logger.enable_sqlite(True)
        self.show_startup_dialog()
        self.setup_ui()
        self.connect_signals()
        self.last_update = time.time()
        self.actual_speed = 0
        
    def show_startup_dialog(self):
        dlg = StartupModeDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.startup_mode = dlg.selected_mode
            self.selected_vehicle = dlg.selected_vehicle
            self.elm327.set_vehicle_mode(self.selected_vehicle)
        else:
            sys.exit(0)

    def setup_ui(self):
        """Configura la interfaz de usuario con pestañas: Selección de PIDs y Visualización de Datos"""
        self.setWindowTitle("🚗 Dashboard OBD-II Optimizado")
        self.setMinimumSize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Estado del sistema
        status_box = QGroupBox("⚡ Estado")
        status_layout = QHBoxLayout(status_box)
        self.connection_status = QLabel("🔴 DESCONECTADO")
        self.protocol_status = QLabel("Protocolo: --")
        self.speed_status = QLabel("⚡ Velocidad: -- Hz")
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.protocol_status)
        status_layout.addWidget(self.speed_status)
        main_layout.addWidget(status_box)

        # Panel de control
        control_box = QGroupBox("🎮 Control")
        control_layout = QHBoxLayout(control_box)
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Modo:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["WiFi", "Emulador"])
        mode_layout.addWidget(self.mode_combo)
        self.connect_btn = QPushButton("🔌 Conectar")
        self.start_fast_btn = QPushButton("⚡ Modo Rápido (5Hz)")
        self.start_normal_btn = QPushButton("🚗 Normal (2Hz)")
        self.stop_btn = QPushButton("⏹️ Detener")
        for btn in [self.connect_btn, self.start_fast_btn, self.start_normal_btn, self.stop_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px;
                    background: #007BFF;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: #0056b3;
                }
                QPushButton:pressed {
                    background: #004085;
                }
            """)
            control_layout.addWidget(btn)
        main_layout.addWidget(control_box)

        # --- NUEVO: Tabs ---
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, stretch=1)

        # Tab 1: Selección de PIDs
        pid_tab = QWidget()
        pid_layout = QVBoxLayout(pid_tab)
        self.pid_selection = PIDCheckboxPanel("Principal", self.elm327.fast_pids)
        self.slow_pid_selection = PIDCheckboxPanel("Secundario", self.elm327.slow_pids)
        self.extended_pid_panel = PIDCheckboxPanel("Extendidos", self.elm327.extended_pids)
        pid_layout.addWidget(self.pid_selection)
        pid_layout.addWidget(self.slow_pid_selection)
        pid_layout.addWidget(self.extended_pid_panel)
        self.apply_pid_btn = QPushButton("✅ Aplicar")
        pid_layout.addWidget(self.apply_pid_btn)
        self.tabs.addTab(pid_tab, "Selección de PIDs")
        self.apply_pid_btn.clicked.connect(self.apply_pid_selection)

        # Tab 2: Visualización de Datos
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_box = QGroupBox("📊 Datos en Tiempo Real")
        grid = QGridLayout(data_box)
        self.fast_data_box = QGroupBox("PIDs Principales")
        self.fast_data_layout = QGridLayout(self.fast_data_box)
        self.pid_labels = {}
        self.slow_data_box = QGroupBox("PIDs Secundarios")
        self.slow_data_layout = QGridLayout(self.slow_data_box)
        self.slow_pid_labels = {}
        self.extended_data_box = QGroupBox("PIDs Extendidos")
        self.extended_data_layout = QGridLayout(self.extended_data_box)
        self.extended_pid_labels = {}
        grid.addWidget(self.fast_data_box, 0, 0)
        grid.addWidget(self.slow_data_box, 0, 1)
        grid.addWidget(self.extended_data_box, 1, 0, 1, 2)
        data_layout.addWidget(data_box)
        self.tabs.addTab(data_tab, "Visualización de Datos")

        # Tab 3: Diagnóstico DTC
        dtc_tab = QWidget()
        dtc_layout = QVBoxLayout(dtc_tab)
        self.dtc_text = QLabel("Códigos DTC:")
        self.dtc_result = QLabel("")
        self.dtc_result.setWordWrap(True)
        self.read_dtc_btn = QPushButton("Leer DTCs")
        self.clear_dtc_btn = QPushButton("Borrar DTCs")
        dtc_layout.addWidget(self.dtc_text)
        dtc_layout.addWidget(self.dtc_result)
        dtc_layout.addWidget(self.read_dtc_btn)
        dtc_layout.addWidget(self.clear_dtc_btn)
        self.tabs.addTab(dtc_tab, "DTC")
        self.read_dtc_btn.clicked.connect(self.read_dtcs)
        self.clear_dtc_btn.clicked.connect(self.clear_dtcs)

        # Botón para escanear PIDs soportados
        self.scan_pids_btn = QPushButton("Escanear PIDs soportados")
        self.scan_pids_btn.setStyleSheet("background-color: #ffb300; color: black; font-weight: bold;")
        self.scan_pids_btn.clicked.connect(self.scan_supported_pids)
        # Insertar el botón en el panel de selección de PIDs (al final del layout)
        # El layout del tab 0 es un QVBoxLayout
        pid_tab = self.tabs.widget(0)
        if pid_tab is not None and hasattr(pid_tab, 'layout') and pid_tab.layout() is not None:
            layout = pid_tab.layout()
            if layout is not None:
                layout.addWidget(self.scan_pids_btn)

        # Menú para cambiar modo/vehículo
        menubar = self.menuBar() if hasattr(self, 'menuBar') else None
        config_menu = menubar.addMenu("Configuración") if menubar else None
        if config_menu is not None:
            self.change_mode_action = QAction("Cambiar modo/vehículo", self)
            config_menu.addAction(self.change_mode_action)
            self.change_mode_action.triggered.connect(self.show_startup_dialog_and_restart)

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
        """
        Alterna la conexión con el dispositivo OBD-II.
        Carga los PIDs y paneles según el modo/vehículo seleccionado.
        """
        try:
            if not self.elm327.connected:
                is_emulator = self.mode_combo.currentText() == "Emulador"
                self.elm327._mode = (OPERATION_MODES["EMULATOR"] if is_emulator else OPERATION_MODES["WIFI"])
                if not is_emulator:
                    self.elm327.ip = "192.168.0.10"
                # --- Selección automática ---
                if self.startup_mode == 'auto':
                    if self.elm327.connect():
                        self.connection_status.setText(
                            "🟢 CONECTADO - " + ("Emulador" if is_emulator else "WiFi")
                        )
                        self.connect_btn.setText("🔌 Desconectar")
                        self.show_protocol_in_status()
                    else:
                        self.connection_status.setText("🔴 ERROR")
                # --- Modo genérico ---
                elif self.startup_mode == 'generic':
                    if self.elm327.connect():
                        self.connection_status.setText(
                            "🟢 CONECTADO - Genérico OBD-II"
                        )
                        self.connect_btn.setText("🔌 Desconectar")
                        # Forzar solo PIDs estándar
                        self.elm327.load_pid_library(protocol=None)
                        self.pid_selection.setup_ui(self.elm327.fast_pids)
                        self.slow_pid_selection.setup_ui(self.elm327.slow_pids)
                        self.extended_pid_panel.setup_ui({})
                    else:
                        self.connection_status.setText("🔴 ERROR")
                # --- Selección de vehículo ---
                elif self.startup_mode == 'vehicle':
                    if self.elm327.connect():
                        self.connection_status.setText(
                            f"🟢 CONECTADO - {self.selected_vehicle or 'Vehículo'}"
                        )
                        self.connect_btn.setText("🔌 Desconectar")
                        # Cargar PIDs específicos
                        if self.selected_vehicle == "Toyota Hilux":
                            self.elm327.load_pid_library(protocol="iso_15765_4_can")
                            self.pid_selection.setup_ui(self.elm327.fast_pids)
                            self.slow_pid_selection.setup_ui(self.elm327.slow_pids)
                            self.extended_pid_panel.setup_ui(self.elm327.extended_pids)
                        elif self.selected_vehicle == "Jeep Grand Cherokee":
                            self.elm327.load_pid_library(protocol="jeep_grand_cherokee")
                            self.pid_selection.setup_ui(self.elm327.fast_pids)
                            self.slow_pid_selection.setup_ui(self.elm327.slow_pids)
                            self.extended_pid_panel.setup_ui(self.elm327.extended_pids)
                        else:
                            self.elm327.load_pid_library(protocol=None)
                            self.pid_selection.setup_ui(self.elm327.fast_pids)
                            self.slow_pid_selection.setup_ui(self.elm327.slow_pids)
                            self.extended_pid_panel.setup_ui({})
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
        # Iniciar hilo de adquisición
        self.reader_thread_stop.clear()
        self.reader_thread = threading.Thread(target=self.data_acquisition_loop, daemon=True)
        self.reader_thread.start()

    def stop_reading(self):
        """Detiene la lectura de datos"""
        self.timer.stop()
        self.slow_timer.stop()
        self.actual_speed = 0
        self.speed_status.setText("⚡ Velocidad: -- Hz")
        self.reader_thread_stop.set()
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=1)
        self.reader_thread = None

    def _refresh_pid_labels(self):
        """Actualiza los labels de los paneles de datos según la selección de PIDs."""
        for layout, labels, pids in [
            (self.fast_data_layout, self.pid_labels, self.selected_fast_pids),
            (self.slow_data_layout, self.slow_pid_labels, self.selected_slow_pids),
            (self.extended_data_layout, self.extended_pid_labels, self.selected_extended_pids)
        ]:
            # Eliminar widgets antiguos de forma segura
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item is not None:
                    widget = item.widget() if hasattr(item, 'widget') else None
                    if widget is not None:
                        widget.deleteLater()
                    else:
                        layout.removeItem(item)
            labels.clear()
            # Crear nuevos labels
            for idx, pid in enumerate(pids):
                label = QLabel(f"{pid}: --")
                label.setStyleSheet('font-size: 16px;')
                layout.addWidget(label, idx, 0)
                labels[pid] = label

    def data_acquisition_loop(self):
        while not self.reader_thread_stop.is_set():
            data = {}
            for pid in self.selected_fast_pids:
                value = self.elm327.query_pid(pid)
                if value is not None and isinstance(value, dict):
                    data[pid] = value
            for pid in self.selected_slow_pids:
                value = self.elm327.query_pid(pid)
                if value is not None and isinstance(value, dict):
                    data[pid] = value
            for pid in self.selected_extended_pids:
                value = self.elm327.query_pid(pid)
                if value is not None and isinstance(value, dict):
                    data[pid] = value
            try:
                self.data_queue.put(data, timeout=0.5)
            except queue.Full:
                pass
            time.sleep(1.0 / (self.actual_speed or 2))

    def read_fast_data(self):
        if not self.elm327.connected:
            return
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get()
                # Actualizar UI y alertas para fast, slow y extendidos
                for pid, value_dict in data.items():
                    if pid in self.pid_labels:
                        label = self.pid_labels[pid]
                        label.setText(f"{value_dict['name']}: {value_dict['value']} {value_dict['unit']}")
                        self.alert_manager.check_and_alert(pid, value_dict['value'], label)
                    elif pid in self.slow_pid_labels:
                        label = self.slow_pid_labels[pid]
                        label.setText(f"{value_dict['name']}: {value_dict['value']} {value_dict['unit']}")
                        self.alert_manager.check_and_alert(pid, value_dict['value'], label)
                    elif pid in self.extended_pid_labels:
                        label = self.extended_pid_labels[pid]
                        label.setText(f"{value_dict['name']}: {value_dict['value']} {value_dict['unit']}")
                        self.alert_manager.check_and_alert(pid, value_dict['value'], label)
                # Logging
                if data and hasattr(self.logger, 'active') and self.logger.active:
                    self.logger.log_data(data)
        except Exception as e:
            print(f"[ERROR] Al consumir la cola de datos: {e}")

    def read_slow_data(self):
        """
        Lee y actualiza los datos SLOW y EXTENDIDOS seleccionados en la interfaz y log.
        Llama a alert_manager para alertas y registra en el logger si está activo.
        """
        if not self.elm327.connected:
            return
        data = {}
        for pid in self.selected_slow_pids:
            value = self.elm327.query_pid(pid)
            if value is not None and isinstance(value, dict):
                data[pid] = value
                if pid in self.slow_pid_labels:
                    label = self.slow_pid_labels[pid]
                    label.setText(f"{value['name']}: {value['value']} {value['unit']}")
                    self.alert_manager.check_and_alert(pid, value['value'], label)
        for pid in self.selected_extended_pids:
            value = self.elm327.query_pid(pid)
            if value is not None and isinstance(value, dict):
                data[pid] = value
                if pid in self.extended_pid_labels:
                    label = self.extended_pid_labels[pid]
                    label.setText(f"{value['name']}: {value['value']} {value['unit']}")
                    self.alert_manager.check_and_alert(pid, value['value'], label)
        if data and hasattr(self.logger, 'active') and self.logger.active:
            self.logger.log_data(data)

    def read_dtcs(self):
        self.dtc_result.setText("Leyendo DTCs...")
        QApplication.processEvents()
        if hasattr(self.elm327, 'read_dtc'):
            dtcs = self.elm327.read_dtc()
            self.dtc_result.setText("\n".join(dtcs))
        else:
            self.dtc_result.setText("[ERROR] Función no disponible")

    def clear_dtcs(self):
        self.dtc_result.setText("Borrando DTCs...")
        QApplication.processEvents()
        if hasattr(self.elm327, 'clear_dtc'):
            ok = self.elm327.clear_dtc()
            if ok:
                self.dtc_result.setText("DTCs borrados correctamente.")
            else:
                self.dtc_result.setText("[ERROR] No se pudieron borrar los DTCs.")
        else:
            self.dtc_result.setText("[ERROR] Función no disponible")

    def scan_supported_pids(self):
        if not self.elm327.connected:
            self.connection_status.setText("🔴 Conecte primero el dispositivo")
            return
        # Aquí podrías implementar un escaneo real de PIDs soportados
        self.connection_status.setText("[INFO] Escaneo de PIDs no implementado aún.")

    def show_protocol_in_status(self):
        proto = self.elm327.detect_protocol()
        if proto:
            self.protocol_status.setText(f"Protocolo: {proto}")
        else:
            self.protocol_status.setText("Protocolo: --")
    def show_startup_dialog_and_restart(self):
        """Permite cambiar el modo/vehículo y reinicia la UI y paneles de PIDs."""
        self.show_startup_dialog()
        # Actualizar paneles de selección de PIDs según vehículo
        self._update_pid_panels_for_vehicle()
        self.apply_pid_selection()

    def _update_pid_panels_for_vehicle(self):
        """Actualiza dinámicamente el panel de PIDs extendidos según el vehículo seleccionado."""
        # Cambiar los PIDs extendidos y sus parsers
        self.elm327.set_vehicle_mode(self.selected_vehicle)
        # Actualizar el panel de selección de extendidos
        self.extended_pid_panel.setup_ui(self.elm327.extended_pids)
        # Forzar refresco de labels
        self._refresh_pid_labels()

    # ...existing code...
    # (El resto de métodos como read_dtcs, clear_dtcs, scan_supported_pids, show_protocol_in_status, etc. siguen igual o pueden ser optimizados en pasos posteriores)
