import json
import logging
import os
import socket
import sys
import time
import random
import threading
import csv
from datetime import datetime

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QGroupBox, QLabel, QMainWindow,
    QMessageBox, QVBoxLayout, QWidget, QPushButton, QHBoxLayout,
    QGridLayout
)

# Constantes
NO_DATA_MSG = "NO DATA"
ERROR_MSG = "ERROR"
LOG_PREFIX = "📊"

# Modos de operación
OPERATION_MODES = {
    "WIFI": "wifi",
    "EMULATOR": "emulator"
}

# Agregar el directorio src al path si existe
if os.path.exists('src'):
    sys.path.append('src')

try:
    # Importaciones básicas OBD
    from src.obd.connection import OBDConnection
    from src.obd.emulador import EmuladorOBD
    from src.obd.test_hilux_emulator import HiluxDieselEmulador
    from src.obd.pid_decoder import PIDDecoder, get_supported_pids
    from src.obd.elm327 import ELM327
    from utils.obd_parsers import parse_pid_response  # Nueva importación
    # Importaciones para autodetección y decodificador universal
    from src.obd.protocol_detector import ProtocolDetector
    from src.utils.logging_app import setup_logging
except ImportError as e:
    print(f"🔧 Usando implementaciones básicas... Error: {e}")
    from obd_connection import OBDConnection
    from obd_emulador import EmuladorOBD
    from utils.logging_app import setup_logging

class OptimizedELM327Connection:
    def __init__(self, ip="192.168.0.10", port=35000, mode="wifi"):
        self.ip = ip
        self.port = port
        self._mode = None  # Modo interno
        self.socket = None
        self.connected = False
        self._data_cache = {}
        self.logger = logging.getLogger('OBD')
        self.logger.setLevel(logging.DEBUG)
        
        # Configurar handler para archivo
        fh = logging.FileHandler('obd_connection.log')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        # Validar y establecer modo
        self.set_mode(mode)
        
        # PIDs optimizados para velocidad (solo los esenciales)
        self.fast_pids = {
            '010C': {'name': 'RPM', 'unit': 'RPM', 'bytes': 2, 
                    'formula': lambda d: ((int(d[0], 16) * 256) + int(d[1], 16)) / 4},
            '010D': {'name': 'Velocidad', 'unit': 'km/h', 'bytes': 1, 
                    'formula': lambda d: int(d[0], 16)},
            '0105': {'name': 'Temp_Motor', 'unit': '°C', 'bytes': 1, 
                    'formula': lambda d: int(d[0], 16) - 40},
            '0104': {'name': 'Carga_Motor', 'unit': '%', 'bytes': 1, 
                    'formula': lambda d: round(int(d[0], 16) * 100 / 255, 1)},
            '0111': {'name': 'Acelerador', 'unit': '%', 'bytes': 1, 
                    'formula': lambda d: round(int(d[0], 16) * 100 / 255, 1)},
        }
        
        # PIDs adicionales (lectura menos frecuente)
        self.slow_pids = {
            '010F': {'name': 'Temp_Admision', 'unit': '°C', 'bytes': 1, 
                    'formula': lambda d: int(d[0], 16) - 40},
            '012F': {'name': 'Combustible', 'unit': '%', 'bytes': 1, 
                    'formula': lambda d: round(int(d[0], 16) * 100 / 255, 1)},
            '0142': {'name': 'Voltaje', 'unit': 'V', 'bytes': 2, 
                    'formula': lambda d: round(((int(d[0], 16) * 256) + 
                                              int(d[1], 16)) / 1000, 2)},
            '010B': {'name': 'Presion_Colector', 'unit': 'kPa', 'bytes': 1, 
                    'formula': lambda d: int(d[0], 16)},
        }
        
    def set_mode(self, mode):
        """Establece el modo de operación con validación"""
        if mode not in OPERATION_MODES.values():
            raise ValueError(f"Modo inválido: {mode}. Debe ser {OPERATION_MODES.values()}")
        
        if self._mode != mode:
            self.logger.info(f"Cambiando modo: {self._mode} -> {mode}")
            self._mode = mode
            self.disconnect()  # Desconectar al cambiar modo
            
    @property
    def mode(self):
        return self._mode
        
    @mode.setter
    def mode(self, value):
        self.set_mode(value)

    def connect(self):
        """Establece conexión con validación de modo y estado"""
        try:
            self.logger.info(f"Iniciando conexión en modo: {self._mode}")
            
            if self._mode == OPERATION_MODES["EMULATOR"]:
                self.logger.warning("⚠️ MODO EMULADOR ACTIVO - Datos simulados")
                self.connected = True
                return True
                
            # Modo WiFi real
            self.logger.info(f"📡 Conectando ELM327 optimizado a {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)
            self.socket.connect((self.ip, self.port))
            
            # Inicialización y verificación
            commands = [
                ("ATZ", 2), ("ATE0", 0.3), ("ATL0", 0.3), 
                ("ATS0", 0.3), ("ATH1", 0.3), ("ATSP0", 0.3), ("0100", 1)
            ]
            
            for cmd, wait in commands:
                self.socket.sendall(f"{cmd}\r".encode())
                time.sleep(wait)
                if wait > 0.5:
                    response = self.socket.recv(512).decode('utf-8', errors='ignore')
                    self.logger.debug(f"Comando {cmd}: {response.strip()[:30]}...")
                    
                    # Verificar respuesta válida
                    if "?" in response or "ERROR" in response:
                        self.logger.error(f"Error en comando {cmd}: {response}")
                        self.disconnect()
                        return False
            
            # Verificación final de conexión real
            self.socket.sendall("0100\r".encode())
            init_response = self.socket.recv(512).decode('utf-8', errors='ignore')
            
            if not self._verify_connection(init_response):
                self.logger.error("Falló verificación de conexión real")
                self.disconnect()
                return False
            
            self.connected = True
            self.logger.info("✅ ELM327 conectado y verificado")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error conexión: {str(e)}")
            self.disconnect()
            return False
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False
    def read_fast_data(self):
        """Lee los PIDs rápidos (datos críticos) del vehículo con validación mejorada."""
        try:
            # Modo emulador
            if self._mode == OPERATION_MODES["EMULATOR"]:
                valid_data = {}
                for pid in self.fast_pids:
                    data = self.query_pid(pid)
                    if data and self._validate_pid_data(pid, data):
                        valid_data[pid] = data
                
                self.fast_data_cache = valid_data
                self._update_display(valid_data, self.fast_labels)
                self.logger.log_data(self.fast_data_cache)
                self._update_log_status()
                return
    
            # Modo WiFi real
            valid_data = {}
            for pid in self.fast_pids:
                data = self.query_pid(pid)
                if data and self._validate_pid_data(pid, data):
                    valid_data[pid] = data
                else:
                    self.logger.warning(f"Datos inválidos para PID {pid}: {data}")
            
            self.fast_data_cache = valid_data
            self._update_display(valid_data, self.fast_labels)
            self.logger.log_data(self.fast_data_cache)
            self._update_log_status()
                    
        except Exception as e:
            self.logger.error(f"Error en read_fast_data: {str(e)}")
    def read_slow_data(self):
        """Lee los PIDs lentos (datos secundarios) del vehículo con validación mejorada."""
        try:
            # Modo emulador
            if self._mode == OPERATION_MODES["EMULATOR"]:
                valid_data = {}
                for pid in self.slow_pids:
                    data = self.query_pid(pid)
                    if data and self._validate_pid_data(pid, data):
                        valid_data[pid] = data
                
                self.slow_data_cache = valid_data
                self._update_display(valid_data, self.slow_labels)
                self.logger.log_data(self.slow_data_cache)
                return
    
            # Modo WiFi real
            valid_data = {}
            for pid in self.slow_pids:
                data = self.query_pid(pid)
                if data and self._validate_pid_data(pid, data):
                    valid_data[pid] = data
                else:
                    self.logger.warning(f"Datos inválidos para PID {pid}: {data}")
            
            self.slow_data_cache = valid_data
            self._update_display(valid_data, self.slow_labels)
            self.logger.log_data(self.slow_data_cache)
                    
        except Exception as e:
            self.logger.error(f"Error en read_slow_data: {str(e)}")
    def _scan_pid_group(self, cmd):
        """Escanea un grupo de PIDs y retorna los soportados con manejo mejorado de errores"""
        try:
            # Validación del comando
            if not cmd or len(cmd) != 4 or not cmd.startswith("01"):
                self.logger.error(f"Comando PID inválido: {cmd}")
                return []
                
            resp = self.elm327.send_pid(cmd)
            if not resp:
                self.logger.warning(f"No hay respuesta para el grupo {cmd}")
                return []
                
            # Limpiar y validar respuesta
            resp = resp.replace(" ", "").upper()
            if "NO DATA" in resp or "ERROR" in resp:
                self.logger.warning(f"Respuesta inválida para grupo {cmd}: {resp}")
                return []
                
            # Verificar formato de respuesta (41 + cmd[2:] + 4 bytes de datos)
            expected_prefix = "41" + cmd[2:]
            if not (resp.startswith(expected_prefix) and len(resp) >= len(expected_prefix) + 8):
                self.logger.error(f"Formato de respuesta inválido para {cmd}: {resp}")
                return []
                
            # Extraer y procesar máscara de bits
            try:
                mask = int(resp[len(expected_prefix):len(expected_prefix) + 8], 16)
                base_pid = int(cmd[2:], 16)
                pids = []
                
                for i in range(32):
                    if mask & (1 << (31 - i)):
                        pid = f"01{base_pid + i + 1:02X}"
                        pids.append(pid)
                        self.logger.debug(f"PID soportado detectado: {pid}")
                        
                return pids
                
            except ValueError as e:
                self.logger.error(f"Error procesando máscara de bits para {cmd}: {e}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error escaneando grupo {cmd}: {e}")
            return []

    def autodetect_protocol_and_scan_pids(self):
        """Autodetecta el protocolo y escanea los PIDs soportados con mejor manejo de errores"""
        try:
            if not self.connection or not self.is_connected:
                self.logger.error("No hay conexión activa")
                self.status_changed.emit("❌ No hay conexión")
                return False
                
            # Inicializar ELM327 con timeout
            self.elm327 = ELM327(self.connection)
            if not self.elm327.initialize():
                self.logger.error("Falló inicialización ELM327")
                self.status_changed.emit("❌ Error de inicialización ELM327")
                return False
            
            # Verificar comunicación básica
            resp = self.elm327.send_command("0100")
            if not resp or "NO DATA" in resp:
                self.logger.error("No hay respuesta del vehículo")
                self.status_changed.emit("❌ Sin respuesta del vehículo")
                return False
                
            self.status_changed.emit("🔍 Detectando PIDs soportados...")
            
            # Escanear grupos de PIDs principales
            pid_groups = ['0100', '0120', '0140', '0160']
            supported_pids = []
            
            for group in pid_groups:
                try:
                    pids = self._scan_pid_group(group)
                    if pids:
                        supported_pids.extend(pids)
                        self.logger.info(f"Grupo {group}: {len(pids)} PIDs")
                except Exception as e:
                    self.logger.warning(f"Error escaneando grupo {group}: {e}")
                    continue
            
            if not supported_pids:
                self.logger.error("No se detectaron PIDs soportados")
                self.status_changed.emit("⚠️ No se encontraron PIDs")
                return False
                
            # Filtrar PIDs prioritarios
            priority_pids = {
                '010C': 'RPM',
                '010D': 'Velocidad',
                '0105': 'Temp. Motor',
                '0104': 'Carga Motor'
            }
            
            self.supported_pids = supported_pids
            self.selected_pids = [
                pid for pid in priority_pids.keys()
                if pid in supported_pids
            ]
            
            if not self.selected_pids:
                self.logger.warning("PIDs prioritarios no soportados")
                # Usar los primeros PIDs encontrados
                self.selected_pids = supported_pids[:5]
                
            msg = (f"✅ {len(self.supported_pids)} PIDs detectados, " +
                  f"{len(self.selected_pids)} seleccionados")
            self.logger.info(msg)
            self.status_changed.emit(msg)
            return True
            
        except Exception as e:
            self.logger.error(f"Error en autodetección: {str(e)}")
            self.status_changed.emit(f"❌ Error: {str(e)}")
            return False
    def read_data(self):
        """Lee datos con mejor manejo de errores y optimización de memoria"""
        if not self.is_connected:
            return {}
            
        self.cleanup_cache()
        
        try:
            # Medir tiempo de lectura para diagnósticos
            start_time = time.time()
            
            # Determinar modo de lectura
            if self.connection_mode == "emulator" and self.emulator:
                data = self._read_emulator_data()
            elif self.connection_mode == "wifi" and self.connection:
                data = self._read_wifi_data()
            else:
                self.logger.error(f"Modo inválido: {self.connection_mode}")
                return {}
                
            # Monitorear rendimiento
            elapsed = time.time() - start_time
            self.performance_monitor.log_read_time(elapsed)
            
            if data:  # Si hay datos válidos
                self._failed_reads = 0  # Resetear contador de errores
            else:
                self._failed_reads += 1
                if self._failed_reads >= self._max_failed_reads:
                    self.logger.error("Demasiados errores consecutivos")
                    self.status_changed.emit("⚠️ Múltiples errores de lectura")
                    self.is_connected = False
                    
            return data
            
        except Exception as e:
            self.logger.error(f"Error en lectura: {str(e)}")
            self._failed_reads += 1
            return {}

    def _read_wifi_data(self):
        """Lee datos por WiFi con mejor manejo de errores y decodificación"""
        if not self.elm327 or not self.selected_pids:
            return {}
            
        data = {}
        start_decode = time.time()
        
        try:
            for pid in self.selected_pids:
                try:
                    # Verificar caché primero
                    if self._should_use_cache(pid):
                        data[pid] = self._get_cached_value(pid)
                        continue
                        
                    # Leer datos del dispositivo
                    raw = self.elm327.send_pid(pid)
                    if not raw or "NO DATA" in raw or "ERROR" in raw:
                        self.logger.warning(f"Error leyendo PID {pid}: {raw}")
                        continue
                        
                    # Limpiar y validar respuesta
                    raw = raw.replace(" ", "").upper()
                    if not (raw.startswith("41" + pid[2:]) and len(raw) >= 4):
                        self.logger.error(f"Respuesta inválida para {pid}: {raw}")
                        continue
                        
                    # Extraer bytes de datos
                    data_bytes = raw[4:]
                    if not data_bytes:
                        continue
                        
                    # Decodificar valor
                    try:
                        decoded = self.pid_decoder.decode(pid, [data_bytes])
                        if decoded and 'value' in decoded:
                            data[pid] = decoded['value']
                            self._cache_data(pid, raw, decoded['value'])
                    except ValueError as e:
                        self.logger.error(f"Error decodificando {pid}: {e}")
                        continue
                        
                except Exception as e:
                    self.logger.error(f"Error procesando PID {pid}: {e}")
                    continue
                    
            # Registrar tiempo de decodificación
            decode_time = time.time() - start_decode
            self.performance_monitor.log_decode_time(decode_time)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error en lectura WiFi: {e}")
            return {}

    def _read_emulator_data(self):
        """Lee datos del emulador con simulación realista"""
        try:
            if not self.emulator or not self.selected_pids:
                return {}
                
            simulated_data = {
                '010C': {
                    'name': 'RPM', 
                    'value': round(720 + random.randint(-20, 20)), 
                    'unit': 'RPM'
                },
                '010D': {
                    'name': 'Velocidad',
                    'value': round(60 + random.randint(-5, 5)), 
                    'unit': 'km/h'
                },
                '0105': {
                    'name': 'Temp_Motor',
                    'value': round(95 + random.randint(-3, 3)), 
                    'unit': '°C'
                },
                '0104': {
                    'name': 'Carga_Motor',
                    'value': round(20.0 + random.uniform(-2, 2), 1), 
                    'unit': '%'
                },
                '0111': {
                    'name': 'Acelerador',
                    'value': round(21.0 + random.uniform(-1, 1), 1), 
                    'unit': '%'
                }
            }
            
            # Filtrar solo PIDs solicitados
            data = {}
            for pid in self.selected_pids:
                if pid in simulated_data:
                    # Usar valor en caché si existe y es reciente
                    if self._should_use_cache(pid):
                        data[pid] = self._get_cached_value(pid)
                    else:
                        value = simulated_data[pid]['value']
                        data[pid] = value
                        self._cache_data(pid, value)
                        
            return data
            
        except Exception as e:
            self.logger.error(f"Error en emulador: {e}")
            return {}

    def _should_use_cache(self, pid):
        """Determina si se debe usar el valor en caché para un PID"""
        cache_entry = self._data_cache.get(pid)
        if not cache_entry:
            return False
            
        # Usar caché solo si el valor es reciente
        age = time.time() - cache_entry['timestamp']
        
        # Diferentes tiempos de caché según el tipo de PID
        max_age = {
            '010C': 0.1,  # RPM: actualización muy rápida
            '010D': 0.2,  # Velocidad: actualización rápida
            '0104': 0.5,  # Carga: actualización media
            '0105': 1.0,  # Temperatura: actualización lenta
            '0111': 0.3   # Acelerador: actualización media-rápida
        }.get(pid, 0.5)  # Valor por defecto
        
        return age < max_age
        
    def _cache_data(self, pid, raw_value=None, decoded_value=None):
        """Almacena datos en caché con timestamp"""
        current_time = time.time()
        
        if raw_value is not None:
            self._data_cache[f"raw_{pid}"] = {
                'value': raw_value,
                'timestamp': current_time
            }
            
        if decoded_value is not None:
            self._data_cache[pid] = {
                'value': decoded_value,
                'timestamp': current_time
            }
            
    def _get_cached_value(self, pid, raw=False):
        """Obtiene valor del caché"""
        key = f"raw_{pid}" if raw else pid
        cache_entry = self._data_cache.get(key)
        return cache_entry['value'] if cache_entry else None
    def _verify_connection(self, response):
        """Verifica que la conexión sea real y no simulada"""
        try:
            # Verificar formato de respuesta OBD
            if not response or len(response) < 4:
                self.logger.error("Respuesta OBD inválida")
                return False
                
            # Verificar que no sea respuesta simulada
            response = response.strip().upper()
            if "EMULATOR" in response or "SIMULATOR" in response:
                self.logger.error("Detectada respuesta de emulador")
                return False
                
            # Verificar respuesta estándar OBD
            if not (response.startswith("41") or response.startswith("7E8")):
                self.logger.error(f"Formato de respuesta inválido: {response}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error en verificación: {str(e)}")
            return False
            
    def _validate_pid_value(self, pid, value):
        """Valida que los valores de los PIDs estén dentro de rangos realistas"""
        try:
            # Rangos realistas para los PIDs principales
            valid_ranges = {
                # RPM: ralentí (500-1000), max 8000
                '010C': {'min': 500, 'max': 8000},  
                # Velocidad: 0-250 km/h
                '010D': {'min': 0, 'max': 250},     
                # Temperatura motor: -40 a 215°C
                '0105': {'min': -40, 'max': 215},   
                # Carga motor: 0-100%
                '0104': {'min': 0, 'max': 100},     
                # Acelerador: 0-100%
                '0111': {'min': 0, 'max': 100},     
                # Temperatura admisión: -40 a 215°C
                '010F': {'min': -40, 'max': 215},   
                # Nivel combustible: 0-100%
                '012F': {'min': 0, 'max': 100},     
                # Voltaje: 8-16V
                '0142': {'min': 8, 'max': 16},      
                # Presión colector: 0-255 kPa
                '010B': {'min': 0, 'max': 255}      
            }
            
            # Verificar si el PID tiene rango definido
            if pid not in valid_ranges:
                self.logger.warning(f"No hay rango definido para PID: {pid}")
                return True
                
            # Obtener rango y validar
            range_info = valid_ranges[pid]
            if not isinstance(value, (int, float)):
                self.logger.error(f"Valor no numérico para {pid}: {value}")
                return False
                
            if value < range_info['min'] or value > range_info['max']:
                self.logger.warning(
                    f"Valor fuera de rango para {pid}: {value} "
                    f"[{range_info['min']}-{range_info['max']}]"
                )
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando valor para {pid}: {str(e)}")
            return False
            
    def _generate_simulated_data(self):
        """Genera datos simulados con valores realistas"""
        return {
            '010C': {
                'name': 'RPM',
                'value': 800 + random.randint(-50, 50),  # Ralentí realista
                'unit': 'RPM'
            },
            '010D': {
                'name': 'Velocidad',
                'value': 0,  # Vehículo detenido
                'unit': 'km/h'
            },
            '0105': {
                'name': 'Temp_Motor',
                'value': 90 + random.randint(-5, 5),  # Temperatura normal
                'unit': '°C'
            },
            '0104': {
                'name': 'Carga_Motor',
                'value': round(15.0 + random.uniform(-2, 2), 1),  # Ralentí
                'unit': '%'
            },
            '0111': {
                'name': 'Acelerador',
                'value': round(5.0 + random.uniform(-1, 1), 1),  # Ralentí
                'unit': '%'
            }
        }
class DataLogger:
    def __init__(self, log_file='obd_data.log', max_size_mb=2.5):
        """
        Inicializa el logger con soporte para emojis y caracteres especiales
        
        Args:
            log_file (str): Nombre del archivo de log
            max_size_mb (float): Tamaño máximo del archivo de log en MB
        """
        self.log_file = log_file
        self.max_size_mb = max_size_mb
        self.logger = logging.getLogger('DataLogger')
        self.logger.setLevel(logging.DEBUG)
        
        # Configurar handler para consola sin emojis
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Configurar handler para archivo con encoding UTF-8 y emojis
        try:
            fh = logging.FileHandler(log_file, encoding='utf-8', mode='a')
            fh.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            fh.setFormatter(file_formatter)
            self.logger.addHandler(fh)
        except Exception as e:
            print(f"Error configurando log file: {str(e)}")
            
        # Diccionario de emojis y sus alternativas en texto
        self.emojis = {
            'error': ('❌', '[ERROR]'),
            'warning': ('⚠️', '[WARN]'),
            'info': ('ℹ️', '[INFO]'),
            'debug': ('🔍', '[DEBUG]'),
            'speed': ('🚗', '[SPEED]'),
            'rpm': ('⚙️', '[RPM]'),
            'temp': ('🌡️', '[TEMP]'),
            'fuel': ('⛽', '[FUEL]'),
            'voltage': ('⚡', '[VOLT]')
        }
    
    def _format_message(self, level, msg):
        """Formatea el mensaje con emoji o texto alternativo según el destino"""
        emoji, alt_text = self.emojis.get(level.lower(), ('📊', '[DATA]'))
        return f"{emoji} {msg}", f"{alt_text} {msg}"
    
    def error(self, msg):
        emoji_msg, alt_msg = self._format_message('error', msg)
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.emit(logging.LogRecord(
                    'DataLogger', logging.ERROR, '', 0, emoji_msg, (), None))
            else:
                handler.emit(logging.LogRecord(
                    'DataLogger', logging.ERROR, '', 0, alt_msg, (), None))
    
    def warning(self, msg):
        emoji_msg, alt_msg = self._format_message('warning', msg)
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.emit(logging.LogRecord(
                    'DataLogger', logging.WARNING, '', 0, emoji_msg, (), None))
            else:
                handler.emit(logging.LogRecord(
                    'DataLogger', logging.WARNING, '', 0, alt_msg, (), None))
    
    def info(self, msg):
        emoji_msg, alt_msg = self._format_message('info', msg)
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.emit(logging.LogRecord(
                    'DataLogger', logging.INFO, '', 0, emoji_msg, (), None))
            else:
                handler.emit(logging.LogRecord(
                    'DataLogger', logging.INFO, '', 0, alt_msg, (), None))
    
    def debug(self, msg):
        emoji_msg, alt_msg = self._format_message('debug', msg)
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.emit(logging.LogRecord(
                    'DataLogger', logging.DEBUG, '', 0, emoji_msg, (), None))
            else:
                handler.emit(logging.LogRecord(
                    'DataLogger', logging.DEBUG, '', 0, alt_msg, (), None))
    
    def log_data(self, data_dict):
        """
        Registra datos del vehículo con formato amigable y emojis
        
        Args:
            data_dict (dict): Diccionario con datos del vehículo
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for pid, data in data_dict.items():
                if isinstance(data, dict):
                    name = data.get('name', '').lower()
                    value = data.get('value', '')
                    unit = data.get('unit', '')
                    
                    emoji = self.emojis.get(name, '📊')
                    log_msg = f"{emoji} {name.title()}: {value} {unit}"
                    self.logger.info(log_msg)
                    
        except Exception as e:
            self.error(f"Error al registrar datos: {str(e)}")
    
    def get_status(self):
        """
        Retorna el estado actual del logger
        
        Returns:
            dict: Estado del logger incluyendo tamaño del archivo
        """
        try:
            size_bytes = os.path.getsize(self.log_file)
            size_mb = round(size_bytes / (1024 * 1024), 2)
            
            return {
                'file': self.log_file,
                'size_mb': size_mb,
                'size_bytes': size_bytes
            }
        except Exception as e:
            self.error(f"Error al obtener estado del logger: {str(e)}")
            return {
                'file': self.log_file,
                'size_mb': 0,
                'size_bytes': 0
            }
class HighSpeedOBDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ Dashboard OBD-II ALTA VELOCIDAD + WiFi + Logging")
        self.setGeometry(50, 50, 1600, 1000)
        self._mode = OPERATION_MODES["WIFI"]  # Modo por defecto
        self.elm327 = OptimizedELM327Connection()
        self.logger = DataLogger(max_size_mb=2.5)
        self.fast_timer = QTimer()
        self.fast_timer.timeout.connect(self.read_fast_data)
        self.slow_timer = QTimer()
        self.slow_timer.timeout.connect(self.read_slow_data)
        self.fast_data_cache = {}
        self.slow_data_cache = {}
        
        # Definir PIDs
        self.fast_pids = ['010C', '010D', '0105', '0104', '0111']
        self.slow_pids = ['010F', '012F', '0142', '010B']
        
        self.init_ui()
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        status_panel = self.create_status_panel()
        main_layout.addWidget(status_panel)
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        fast_data_panel = self.create_fast_data_panel()
        main_layout.addWidget(fast_data_panel)
        slow_data_panel = self.create_slow_data_panel()
        main_layout.addWidget(slow_data_panel)
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Dashboard Alta Velocidad - Listo")
    def create_status_panel(self):
        group_box = QGroupBox("⚡ Estado del Sistema")
        layout = QHBoxLayout(group_box)
        self.connection_status = QLabel("🔴 DESCONECTADO")
        self.connection_status.setStyleSheet("""
            font-weight: bold; font-size: 16px; color: red;
            padding: 10px; background-color: #FFE4E1;
            border: 2px solid red; border-radius: 5px;
        """)
        layout.addWidget(self.connection_status)
        self.logging_status = QLabel("📝 Logging: Inactivo")
        self.logging_status.setStyleSheet("""
            font-weight: bold; font-size: 14px; color: #555;
            padding: 10px; background-color: #F0F8FF;
            border: 2px solid #4169E1; border-radius: 5px;
        """)
        layout.addWidget(self.logging_status)
        self.speed_status = QLabel("⚡ Velocidad: -- Hz")
        self.speed_status.setStyleSheet("""
            font-weight: bold; font-size: 14px; color: #228B22;
            padding: 10px; background-color: #F0FFF0;
            border: 2px solid #228B22; border-radius: 5px;
        """)
        layout.addWidget(self.speed_status)
        layout.addStretch()
        return group_box
    def create_control_panel(self):
        group_box = QGroupBox("🎮 Control Alta Velocidad")
        layout = QHBoxLayout(group_box)
        # Selector de modo
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Modo:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["WiFi ELM327", "Emulador (Test)"])
        self.mode_combo.setCurrentIndex(0)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)
        self.connect_btn = QPushButton("🔌 Conectar")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("""
            font-weight: bold; padding: 12px; font-size: 14px;
            background-color: #4CAF50; color: white; border: none; border-radius: 6px;
        """)
        layout.addWidget(self.connect_btn)
        self.start_fast_btn = QPushButton("⚡ Modo Rápido (5Hz)")
        self.start_fast_btn.clicked.connect(self.start_fast_mode)
        self.start_fast_btn.setEnabled(False)
        self.start_fast_btn.setStyleSheet("""
            font-weight: bold; padding: 12px; font-size: 14px;
            background-color: #FF5722; color: white; border: none; border-radius: 6px;
        """)
        layout.addWidget(self.start_fast_btn)
        self.start_normal_btn = QPushButton("🚗 Modo Normal (2Hz)")
        self.start_normal_btn.clicked.connect(self.start_normal_mode)
        self.start_normal_btn.setEnabled(False)
        self.start_normal_btn.setStyleSheet("""
            font-weight: bold; padding: 12px; font-size: 14px;
            background-color: #2196F3; color: white; border: none; border-radius: 6px;
        """)
        layout.addWidget(self.start_normal_btn)
        self.stop_btn = QPushButton("⏹️ Detener")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            font-weight: bold; padding: 12px; font-size: 14px;
            background-color: #9E9E9E; color: white; border: none; border-radius: 6px;
        """)
        layout.addWidget(self.stop_btn)
        layout.addStretch()
        return group_box
    def create_fast_data_panel(self):
        """Crea el panel de datos de alta frecuencia con estilo mejorado"""
        group_box = QGroupBox("⚡ Datos en Tiempo Real")
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #4CAF50;
                border-radius: 6px;
                margin-top: 6px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 7px;
                padding: 0px 5px 0px 5px;
                background-color: #4CAF50;
                color: white;
                border-radius: 3px;
            }
        """)
        
        layout = QGridLayout(group_box)
        layout.setSpacing(10)
        
        # Crear contenedores individuales para cada métrica
        self.fast_labels = {}
        
        # RPM
        rpm_container = QGroupBox("⚙️ RPM")
        rpm_layout = QVBoxLayout(rpm_container)
        self.fast_labels['010C'] = QLabel("----")
        self.fast_labels['010C'].setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #2196F3;
            padding: 10px;
            background-color: #E3F2FD;
            border: 1px solid #90CAF9;
            border-radius: 4px;
        """)
        rpm_layout.addWidget(self.fast_labels['010C'])
        layout.addWidget(rpm_container, 0, 0)
        
        # Velocidad
        speed_container = QGroupBox("🚗 Velocidad")
        speed_layout = QVBoxLayout(speed_container)
        self.fast_labels['010D'] = QLabel("----")
        self.fast_labels['010D'].setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
            padding: 10px;
            background-color: #E8F5E9;
            border: 1px solid #A5D6A7;
            border-radius: 4px;
        """)
        speed_layout.addWidget(self.fast_labels['010D'])
        layout.addWidget(speed_container, 0, 1)
        
        # Temperatura del Motor
        temp_container = QGroupBox("🌡️ Temperatura Motor")
        temp_layout = QVBoxLayout(temp_container)
        self.fast_labels['0105'] = QLabel("----")
        self.fast_labels['0105'].setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #F44336;
            padding: 10px;
            background-color: #FFEBEE;
            border: 1px solid #FFCDD2;
            border-radius: 4px;
        """)
        temp_layout.addWidget(self.fast_labels['0105'])
        layout.addWidget(temp_container, 0, 2)
        
        # Carga del Motor
        load_container = QGroupBox("💪 Carga Motor")
        load_layout = QVBoxLayout(load_container)
        self.fast_labels['0104'] = QLabel("----")
        self.fast_labels['0104'].setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #FF9800;
            padding: 10px;
            background-color: #FFF3E0;
            border: 1px solid #FFE0B2;
            border-radius: 4px;
        """)
        load_layout.addWidget(self.fast_labels['0104'])
        layout.addWidget(load_container, 1, 0)
        
        # Posición del Acelerador
        throttle_container = QGroupBox("🎮 Acelerador")
        throttle_layout = QVBoxLayout(throttle_container)
        self.fast_labels['0111'] = QLabel("----")
        self.fast_labels['0111'].setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #9C27B0;
            padding: 10px;
            background-color: #F3E5F5;
            border: 1px solid #E1BEE7;
            border-radius: 4px;
        """)
        throttle_layout.addWidget(self.fast_labels['0111'])
        layout.addWidget(throttle_container, 1, 1)
        
        return group_box

    def create_slow_data_panel(self):
        group_box = QGroupBox("📊 Datos Adicionales (Actualización Normal)")
        layout = QGridLayout(group_box)
        self.slow_labels = {}
        slow_pids = ['010F', '012F', '0142', '010B']
        for i, pid in enumerate(slow_pids):
            info = self.elm327.slow_pids[pid]
            name_label = QLabel(f"{info['name']}:")
            name_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #555;")
            value_label = QLabel("--")
            value_label.setStyleSheet("""
                font-weight: bold; font-size: 16px; color: #1976D2;
                border: 2px solid #1976D2; padding: 8px; 
                background-color: #E3F2FD; min-width: 100px; 
                border-radius: 6px; text-align: center;
            """)
            layout.addWidget(name_label, 0, i * 2)
            layout.addWidget(value_label, 0, i * 2 + 1)
            self.slow_labels[pid] = value_label
        return group_box
    def toggle_connection(self):
        if not self.elm327.connected:
            mode = self.mode_combo.currentText()
            if "Emulador" in mode:
                self.elm327.connected = True
                self.elm327.mode = "emulator"
                self.connection_status.setText("🟡 EMULADOR ACTIVO")
                self.connection_status.setStyleSheet("""
                    font-weight: bold; font-size: 16px; color: orange;
                    padding: 10px; background-color: #FFF8DC;
                    border: 2px solid orange; border-radius: 5px;
                """)
                self.connect_btn.setText("🔌 Desconectar")
                self.start_fast_btn.setEnabled(True)
                self.start_normal_btn.setEnabled(True)
                print("✅ Modo emulador activado")
            else:
                if self.elm327.connect():
                    self.connection_status.setText("🟢 CONECTADO OPTIMIZADO")
                    self.connection_status.setStyleSheet("""
                        font-weight: bold; font-size: 16px; color: green;
                        padding: 10px; background-color: #F0FFF0;
                        border: 2px solid green; border-radius: 5px;
                    """)
                    self.connect_btn.setText("🔌 Desconectar")
                    self.start_fast_btn.setEnabled(True)
                    self.start_normal_btn.setEnabled(True)
                    print("✅ Conexión optimizada establecida")
        else:
            self.stop_monitoring()
            self.elm327.disconnect()
            self.connection_status.setText("🔴 DESCONECTADO")
            self.connection_status.setStyleSheet("""
                font-weight: bold; font-size: 16px; color: red;
                padding: 10px; background-color: #FFE4E1;
                border: 2px solid red; border-radius: 5px;
            """)
            self.connect_btn.setText("🔌 Conectar")
            self.start_fast_btn.setEnabled(False)
            self.start_normal_btn.setEnabled(False)
    def start_fast_mode(self):
        self.fast_timer.start(200)
        self.slow_timer.start(2000)
        self.start_fast_btn.setEnabled(False)
        self.start_normal_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.speed_status.setText("⚡ Velocidad: 5 Hz (Ultra Rápido)")
        print("⚡ Modo alta velocidad activado: 5 Hz")
    def start_normal_mode(self):
        self.fast_timer.start(500)
        self.slow_timer.start(2000)
        self.start_fast_btn.setEnabled(False)
        self.start_normal_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.speed_status.setText("🚗 Velocidad: 2 Hz (Normal)")
        print("🚗 Modo normal activado: 2 Hz")
    def stop_monitoring(self):
        self.fast_timer.stop()
        self.slow_timer.stop()
        self.start_fast_btn.setEnabled(True)
        self.start_normal_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.speed_status.setText("⚡ Velocidad: Detenido")
        print("⏹️ Monitoreo detenido")
    def read_fast_data(self):
        """Lee los PIDs rápidos (datos críticos) del vehículo con validación mejorada."""
        try:
            # Modo emulador
            if self._mode == OPERATION_MODES["EMULATOR"]:
                valid_data = {}
                for pid in self.fast_pids:
                    data = self.query_pid(pid)
                    if data and self._validate_pid_data(pid, data):
                        valid_data[pid] = data
                
                self.fast_data_cache = valid_data
                self._update_display(valid_data, self.fast_labels)
                self.logger.log_data(self.fast_data_cache)
                self._update_log_status()
                return
    
            # Modo WiFi real
            valid_data = {}
            for pid in self.fast_pids:
                data = self.query_pid(pid)
                if data and self._validate_pid_data(pid, data):
                    valid_data[pid] = data
                else:
                    self.logger.warning(f"Datos inválidos para PID {pid}: {data}")
            
            self.fast_data_cache = valid_data
            self._update_display(valid_data, self.fast_labels)
            self.logger.log_data(self.fast_data_cache)
            self._update_log_status()
                    
        except Exception as e:
            self.logger.error(f"Error en read_fast_data: {str(e)}")
    def read_slow_data(self):
        """Lee los PIDs lentos (datos secundarios) del vehículo con validación mejorada."""
        try:
            # Modo emulador
            if self._mode == OPERATION_MODES["EMULATOR"]:
                valid_data = {}
                for pid in self.slow_pids:
                    data = self.query_pid(pid)
                    if data and self._validate_pid_data(pid, data):
                        valid_data[pid] = data
                
                self.slow_data_cache = valid_data
                self._update_display(valid_data, self.slow_labels)
                self.logger.log_data(self.slow_data_cache)
                return
    
            # Modo WiFi real
            valid_data = {}
            for pid in self.slow_pids:
                data = self.query_pid(pid)
                if data and self._validate_pid_data(pid, data):
                    valid_data[pid] = data
                else:
                    self.logger.warning(f"Datos inválidos para PID {pid}: {data}")
            
            self.slow_data_cache = valid_data
            self._update_display(valid_data, self.slow_labels)
            self.logger.log_data(self.slow_data_cache)
                    
        except Exception as e:
            self.logger.error(f"Error en read_slow_data: {str(e)}")
    def _validate_pid_data(self, pid, data):
        """Valida los datos recibidos de un PID"""
        if not isinstance(data, dict):
            return False
            
        required_keys = ['value', 'unit']
        if not all(key in data for key in required_keys):
            return False
            
        # Validar rangos según el tipo de PID
        if pid == '010C':  # RPM
            return 0 <= data['value'] <= 8000
        elif pid == '010D':  # Velocidad
            return 0 <= data['value'] <= 255
        elif pid == '0105':  # Temp Motor
            return -40 <= data['value'] <= 215
        elif pid == '0104':  # Carga Motor
            return 0 <= data['value'] <= 100
        elif pid == '0111':  # Posición Acelerador
            return 0 <= data['value'] <= 100
            
        return True

    def _update_display(self, pid_data, labels):
        """Actualiza las etiquetas de la interfaz con los datos validados"""
        for pid, value_label in labels.items():
            if pid in pid_data:
                data = pid_data[pid]
                if self._validate_pid_data(pid, data):
                    value_label.setText(f"{data['value']} {data['unit']}")
                else:
                    value_label.setText("ERR")
                    self.logger.warning(f"Datos inválidos para PID {pid}: {data}")

    def _update_log_status(self):
        """Actualiza el estado del registro en la interfaz"""
        try:
            log_status = self.logger.get_status()
            self.logging_status.setText(
                f"📝 Log: {log_status['file']} ({log_status['size_mb']}MB)")
        except Exception as e:
            self.logger.error(f"Error actualizando estado del log: {str(e)}")

    def query_pid(self, pid):
        """Consulta un PID específico y retorna el valor decodificado"""
        try:
            # Modo emulador
            if self._mode == OPERATION_MODES["EMULATOR"]:
                simulated_data = {
                    '010C': lambda: random.randint(700, 1000),  # RPM
                    '010D': lambda: random.randint(0, 80),      # Velocidad
                    '0105': lambda: random.randint(80, 95),     # Temperatura
                    '0104': lambda: random.randint(10, 30),     # Carga
                    '0111': lambda: random.randint(0, 20)       # Acelerador
                }
                return simulated_data.get(pid, lambda: 0)()

            # Modo WiFi real
            if not self.socket:
                self.logger.error("Socket no inicializado")
                return None

            # Enviar comando y esperar respuesta
            cmd = f"{pid}\r"
            self.socket.sendall(cmd.encode())
            response = self.socket.recv(1024).decode('utf-8', errors='ignore')
            
            # Limpiar y validar respuesta
            response = response.strip().replace('\r', '').replace('\n', '')
            if "NO DATA" in response or "ERROR" in response or "?" in response:
                self.logger.warning(f"Sin datos para PID {pid}: {response}")
                return None

            # Extraer bytes de datos
            if not response.startswith("41"):
                self.logger.error(f"Respuesta inválida para {pid}: {response}")
                return None

            data_bytes = response[4:].split()
            if not data_bytes:
                return None

            # Aplicar fórmula según PID
            if pid in self.fast_pids:
                formula = self.fast_pids[pid]['formula']
                try:
                    value = formula(data_bytes)
                    if self._validate_pid_data(pid, value):
                        return value
                except Exception as e:
                    self.logger.error(f"Error decodificando {pid}: {e}")
                    return None

            return None

        except Exception as e:
            self.logger.error(f"Error en query_pid {pid}: {str(e)}")
            return None
def main():
    """Función principal que inicia el dashboard."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    print("⚡ Dashboard OBD-II Alta Velocidad + WiFi + Logging Automático")
    print("🚀 Optimizado para velocidad máxima")
    print("📝 Logging automático < 2.5MB por archivo")
    dashboard = HighSpeedOBDDashboard()
    dashboard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
