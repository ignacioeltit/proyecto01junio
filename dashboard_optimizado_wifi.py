import sys
import os
import socket
import time
import csv
import threading
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QGridLayout, QApplication, QMessageBox,
    QComboBox
)
from PyQt6.QtCore import QTimer

# --- INTEGRACIÓN SISTEMA DETECCIÓN AUTOMÁTICA ---
try:
    from src.vehicle_detection.vehicle_identifier import VehicleIdentifier
    from src.vehicle_detection.vehicle_database import VEHICLE_DATABASE
    VEHICLE_DETECTION_AVAILABLE = True
except ImportError:
    VEHICLE_DETECTION_AVAILABLE = False
    print("Módulos de detección no disponibles - funcionando en modo básico")

class OptimizedELM327Connection:
    def __init__(self, ip="192.168.0.10", port=35000, mode="wifi"):
        self.ip = ip
        self.port = port
        self.mode = mode  # NUEVO
        self.socket = None
        self.connected = False
        # PIDs optimizados para velocidad (solo los esenciales)
        self.fast_pids = {
            '010C': {'name': 'RPM', 'unit': 'RPM', 'bytes': 2, 'formula': lambda d: ((int(d[0], 16) * 256) + int(d[1], 16)) / 4},
            '010D': {'name': 'Velocidad', 'unit': 'km/h', 'bytes': 1, 'formula': lambda d: int(d[0], 16)},
            '0105': {'name': 'Temp_Motor', 'unit': '°C', 'bytes': 1, 'formula': lambda d: int(d[0], 16) - 40},
            '0104': {'name': 'Carga_Motor', 'unit': '%', 'bytes': 1, 'formula': lambda d: round(int(d[0], 16) * 100 / 255, 1)},
            '0111': {'name': 'Acelerador', 'unit': '%', 'bytes': 1, 'formula': lambda d: round(int(d[0], 16) * 100 / 255, 1)},
        }
        # PIDs adicionales (lectura menos frecuente)
        self.slow_pids = {
            '010F': {'name': 'Temp_Admision', 'unit': '°C', 'bytes': 1, 'formula': lambda d: int(d[0], 16) - 40},
            '012F': {'name': 'Combustible', 'unit': '%', 'bytes': 1, 'formula': lambda d: round(int(d[0], 16) * 100 / 255, 1)},
            '0142': {'name': 'Voltaje', 'unit': 'V', 'bytes': 2, 'formula': lambda d: round(((int(d[0], 16) * 256) + int(d[1], 16)) / 1000, 2)},
            '010B': {'name': 'Presion_Colector', 'unit': 'kPa', 'bytes': 1, 'formula': lambda d: int(d[0], 16)},
        }    def connect(self):
        """Establece conexión con el adaptador ELM327"""
        try:
            print(f"📡 Conectando ELM327 optimizado a {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # Incrementado a 5 segundos
            self.socket.connect((self.ip, self.port))

            # Reset completo
            self._clear_socket_buffer()
            self.socket.sendall("ATZ\r".encode())
            time.sleep(2)  # Esperar reset completo
            response = self._read_socket()
            
            if "ELM327" not in response:
                print("❌ No se detectó ELM327")
                self.disconnect()
                return False

            # Configuración inicial con verificación
            init_commands = [
                ("ATE0", "Echo off"),
                ("ATL0", "Linefeeds off"), 
                ("ATH0", "Headers off"),
                ("ATS0", "Spaces off"),
                ("ATI", "Get ID"),
                ("ATSP0", "Auto protocol"),
            ]

            for cmd, desc in init_commands:
                print(f"   {desc}...")
                self.socket.sendall(f"{cmd}\r".encode())
                time.sleep(0.3)
                response = self._read_socket()
                
                if not response or "ERROR" in response:
                    print(f"❌ Error en {desc}")
                    self.disconnect()
                    return False
            
            # Verificar comunicación con ECU
            self.socket.sendall("0100\r".encode())
            time.sleep(1)
            response = self._read_socket()

            if "41 00" in response or "4100" in response:
                # Detectar y configurar protocolo
                if not self._detect_and_set_protocol():
                    print("❌ Error detectando protocolo")
                    self.disconnect()
                    return False
                    
                self.connected = True
                print("✅ ELM327 optimizado conectado y configurado")
                return True
            else:
                print("❌ No hay comunicación con la ECU")
                self.disconnect()
                return False

        except Exception as e:
            print(f"❌ Error conexión: {e}")
            self.disconnect()
            return False
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False
    def read_fast_data(self):
        """Lectura rápida de PIDs principales - VERSION OPTIMIZADA Y ROBUSTA"""
        if not self.connected:
            return {}
            
        if hasattr(self, 'mode') and self.mode == "emulator":
            import random
            simulated_data = {
                '010C': {'name': 'RPM', 'value': 800 + random.randint(-50, 50), 'unit': 'RPM'},
                '010D': {'name': 'Velocidad', 'value': 60 + random.randint(-5, 5), 'unit': 'km/h'},
                '0105': {'name': 'Temp_Motor', 'value': 85 + random.randint(-2, 2), 'unit': '°C'},
                '0104': {'name': 'Carga_Motor', 'value': 45 + random.randint(-5, 5), 'unit': '%'},
                '0111': {'name': 'Acelerador', 'value': 20 + random.randint(-3, 3), 'unit': '%'},
            }
            return simulated_data
            
        data = {}
        
        try:
            # 1. Limpiar buffer por si quedó algo
            self.socket.settimeout(0.1)
            try:
                self.socket.recv(1024)
            except:
                pass
                
            # 2. Restaurar timeout normal
            self.socket.settimeout(0.5)
            
            for pid in self.fast_pids:
                try:
                    # 3. Enviar comando con retorno de carro
                    self.socket.sendall(f"{pid}\r".encode())
                    
                    # 4. Esperar respuesta con timeout corto
                    response = ""
                    start_time = time.time()
                    
                    while True:
                        try:
                            chunk = self.socket.recv(256).decode('utf-8', errors='ignore')
                            if chunk:
                                response += chunk
                                
                            # 5. Criterios de salida
                            if '>' in response or 'NO DATA' in response:
                                break
                                
                            if time.time() - start_time > 0.3:  # Timeout de seguridad
                                break
                                
                        except socket.timeout:
                            break
                            
                    # 6. Parsear solo si hay respuesta
                    if response:
                        parsed = self.parse_response(response, pid)
                        if parsed:
                            # 7. Validar rango de valores
                            if self._validate_pid_value(pid, parsed['value']):
                                data[pid] = parsed
                    
                except Exception as e:
                    print(f"Error leyendo PID {pid}: {e}")
                    continue
                    
            return data
            
        except Exception as e:
            print(f"Error en read_fast_data: {e}")
            return {}

    def parse_response(self, response, pid):
        """Parsea respuesta del ELM327 - VERSIÓN ROBUSTA"""
        try:
            # 1. Limpieza básica de la respuesta
            lines = response.replace('\r', '').replace('SEARCHING...', '').split('\n')
            lines = [l.strip() for l in lines if l.strip() and 'NO DATA' not in l]
            
            # 2. Preparar respuesta para parseo
            clean_response = ''
            for line in lines:
                # Remover '>' y caracteres de control
                line = line.replace('>', '').strip()
                if line.startswith('41'):
                    clean_response = line
                    break
            
            if not clean_response:
                return None
                
            # 3. Separar bytes y validar formato
            bytes_list = clean_response.replace(' ', '')
            if len(bytes_list) < 4:
                return None
                
            # 4. Validar que la respuesta corresponde al PID solicitado
            if not bytes_list.startswith('41' + pid[2:4]):
                return None
                
            # 5. Extraer y parsear datos según el tipo de PID
            data_start = 4  # Posición después de 41XX
            
            if pid == '010C':  # RPM
                if len(bytes_list) >= data_start + 4:
                    try:
                        a = int(bytes_list[data_start:data_start+2], 16)
                        b = int(bytes_list[data_start+2:data_start+4], 16)
                        rpm = ((a * 256) + b) / 4.0
                        return {'name': 'RPM', 'value': int(rpm), 'unit': 'RPM'}
                    except ValueError:
                        pass
                        
            elif pid == '010D':  # Velocidad
                if len(bytes_list) >= data_start + 2:
                    try:
                        speed = int(bytes_list[data_start:data_start+2], 16)
                        return {'name': 'Velocidad', 'value': speed, 'unit': 'km/h'}
                    except ValueError:
                        pass
                        
            elif pid == '0105':  # Temperatura motor
                if len(bytes_list) >= data_start + 2:
                    try:
                        temp = int(bytes_list[data_start:data_start+2], 16) - 40
                        return {'name': 'Temp_Motor', 'value': temp, 'unit': '°C'}
                    except ValueError:
                        pass
                        
            elif pid == '0104':  # Carga motor
                if len(bytes_list) >= data_start + 2:
                    try:
                        load = int(bytes_list[data_start:data_start+2], 16) * 100.0 / 255.0
                        return {'name': 'Carga_Motor', 'value': round(load, 1), 'unit': '%'}
                    except ValueError:
                        pass
                        
            elif pid == '0111':  # Posición acelerador
                if len(bytes_list) >= data_start + 2:
                    try:
                        throttle = int(bytes_list[data_start:data_start+2], 16) * 100.0 / 255.0
                        return {'name': 'Acelerador', 'value': round(throttle, 1), 'unit': '%'}
                    except ValueError:
                        pass
                        
            return None
            
        except Exception as e:
            print(f"Error en parse_response: {e}")
            return None

    def read_slow_data(self):
        # Modo emulador
        if hasattr(self, 'mode') and self.mode == "emulator":
            import random
            simulated_slow_data = {
                '010F': {'name': 'Temp_Admision', 'value': 25 + random.randint(-3, 3), 'unit': '°C'},
                '012F': {'name': 'Combustible', 'value': round(75 + random.uniform(-5, 5), 1), 'unit': '%'},
                '0142': {'name': 'Voltaje', 'value': round(12.5 + random.uniform(-0.3, 0.3), 2), 'unit': 'V'},
                '010B': {'name': 'Presion_Colector', 'value': 100 + random.randint(-5, 5), 'unit': 'kPa'},
            }
            return simulated_slow_data
        # Código WiFi real (idéntico al original)
        if not self.connected:
            return {}
        data = {}
        for pid, info in self.slow_pids.items():
            try:
                self.socket.sendall(f"{pid}\r".encode())
                time.sleep(0.1)
                response = self.socket.recv(256).decode('utf-8', errors='ignore')
                if '41' in response and 'NODATA' not in response:
                    parts = response.replace('\r', '').replace('\n', '').replace('>', '').split()
                    for i, part in enumerate(parts):
                        if part == '41' and i + 1 < len(parts) and parts[i + 1] == pid[2:4]:
                            data_start = i + 2
                            if data_start < len(parts):
                                data_bytes = []
                                for j in range(info['bytes']):
                                    if data_start + j < len(parts):
                                        try:
                                            int(parts[data_start + j], 16)
                                            data_bytes.append(parts[data_start + j])
                                        except:
                                            break
                                if len(data_bytes) == info['bytes']:
                                    value = info['formula'](data_bytes)
                                    data[pid] = {
                                        'name': info['name'],
                                        'value': value,
                                        'unit': info['unit']
                                    }
                            break
            except:
                continue
        return data

    def _detect_and_set_protocol(self):
        """Detecta y configura el protocolo OBD-II con fallback automático"""
        try:
            protocols = [
                ("ATSP0", "Auto"),             # Auto primero
                ("ATSP6", "ISO 15765-4 CAN"),  # CAN 11/500
                ("ATSP8", "ISO 15765-4 CAN"),  # CAN 11/250
                ("ATSP7", "ISO 15765-4 CAN"),  # CAN 29/500
                ("ATSP9", "ISO 15765-4 CAN"),  # CAN 29/250
                ("ATSP3", "ISO 9141-2"),       # ISO 
                ("ATSP4", "ISO 14230-4 KWP"),  # KWP fast
                ("ATSP5", "ISO 14230-4 KWP"),  # KWP 5-baud
                ("ATSP1", "SAE J1850 PWM"),    # J1850 PWM
                ("ATSP2", "SAE J1850 VPW")     # J1850 VPW
            ]

            if not self._initialize_adapter():
                return False

            for protocol_cmd, protocol_name in protocols:
                if self._try_protocol(protocol_cmd, protocol_name):
                    return True
                    
            self.logger.error("❌ No se detectó protocolo")
            return False
            
        except Exception as e:
            self.logger.error(f"Error en detección: {str(e)}")
            return False
            
    def _initialize_adapter(self):
        """Inicializa el adaptador ELM327"""
        try:
            # Reset
            self.socket.sendall("ATZ\r".encode())
            time.sleep(1)
            
            # Comandos de inicialización
            init_commands = [
                "ATE0",  # Echo off
                "ATL0",  # Linefeeds off
                "ATH0",  # Headers off
                "ATS0",  # Spaces off
                "ATI",   # Identificación
            ]
            
            for cmd in init_commands:
                self.socket.sendall(f"{cmd}\r".encode())
                time.sleep(0.1)
                resp = self._read_socket()
                if not resp or "ERROR" in resp:
                    self.logger.warning(f"Fallo en comando {cmd}")
                    continue
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando: {str(e)}")
            return False
            
    def _try_protocol(self, protocol_cmd, protocol_name):
        """Intenta establecer un protocolo específico"""
        try:
            self.logger.info(f"Probando: {protocol_name}")
            
            # Enviar comando de protocolo
            self.socket.sendall(f"{protocol_cmd}\r".encode())
            time.sleep(0.2)
            resp = self._read_socket()
            
            if "OK" not in resp:
                self.logger.warning(f"No OK en {protocol_name}")
                return False

            # Verificar conexión con ECU
            for _ in range(3):
                self.socket.sendall("0100\r".encode())
                time.sleep(0.3)
                resp = self._read_socket()
                
                if "UNABLE TO CONNECT" in resp or "NO DATA" in resp:
                    continue
                    
                if "41 00" in resp or "4100" in resp:
                    self.logger.info(f"✅ Protocolo: {protocol_name}")
                    self._current_protocol = protocol_name
                    self.socket.settimeout(5)
                    return True
                    
            self._clear_socket_buffer()
            return False
            
        except Exception as e:
            self.logger.warning(f"Error en {protocol_name}")
            self.logger.debug(str(e))
            return False
            
    def _read_socket(self):
        """Lee datos del socket con manejo de errores"""
        try:
            return self.socket.recv(1024).decode('utf-8', errors='ignore')
        except socket.timeout:
            return ""
        except Exception as e:
            self.logger.error(f"Error leyendo socket: {str(e)}")
            return ""
            
    def _clear_socket_buffer(self):
        """Limpia el buffer del socket"""
        self.socket.settimeout(0.1)
        try:
            while True:
                self.socket.recv(1024)
        except socket.timeout:
            pass
        self.socket.settimeout(3)

    def _validate_pid_value(self, pid, value):
        """Valida que los valores de los PIDs estén dentro de rangos realistas"""
        try:
            # Rangos válidos para cada PID
            ranges = {
                '010C': (0, 8000),      # RPM: 0-8000
                '010D': (0, 255),        # Velocidad: 0-255 km/h
                '0105': (-40, 215),      # Temperatura: -40 a 215°C
                '0104': (0, 100),        # Carga motor: 0-100%
                '0111': (0, 100),        # Acelerador: 0-100%
                '010F': (-40, 215),      # Temperatura admisión: -40 a 215°C
                '012F': (0, 100),        # Nivel combustible: 0-100%
                '0142': (0, 20),         # Voltaje batería: 0-20V
                '010B': (0, 255)         # MAP: 0-255 kPa
            }
            
            # Si el PID no está en la lista de rangos, aceptamos el valor
            if pid not in ranges:
                return True
                
            min_val, max_val = ranges[pid]
            return min_val <= value <= max_val
            
        except Exception as e:
            print(f"Error en validación de PID {pid}: {e}")
            return False
class DataLogger:
    def __init__(self, max_size_mb=2.5):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_file = None
        self.file_counter = 1
        self.current_size = 0
        self.csv_writer = None
        self.csv_file = None
        self.lock = threading.Lock()
        self.log_dir = "logs_obd"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.start_new_file()
    def start_new_file(self):
        with self.lock:
            if self.csv_file:
                self.csv_file.close()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"obd_log_{timestamp}_{self.file_counter:03d}.csv"
            filepath = os.path.join(self.log_dir, filename)
            self.csv_file = open(filepath, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            header = ['timestamp', 'rpm', 'velocidad', 'temp_motor', 'carga_motor', 
                     'acelerador', 'temp_admision', 'combustible', 'voltaje', 'presion_colector']
            self.csv_writer.writerow(header)
            self.csv_file.flush()
            self.current_size = 0
            self.current_file = filepath
            print(f"📝 Nuevo log iniciado: {filename}")
    def log_data(self, fast_data, slow_data):
        with self.lock:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                rpm = fast_data.get('010C', {}).get('value', 0)
                velocidad = fast_data.get('010D', {}).get('value', 0)
                temp_motor = fast_data.get('0105', {}).get('value', 0)
                carga_motor = fast_data.get('0104', {}).get('value', 0)
                acelerador = fast_data.get('0111', {}).get('value', 0)
                temp_admision = slow_data.get('010F', {}).get('value', 0)
                combustible = slow_data.get('012F', {}).get('value', 0)
                voltaje = slow_data.get('0142', {}).get('value', 0)
                presion_colector = slow_data.get('010B', {}).get('value', 0)
                row = [timestamp, rpm, velocidad, temp_motor, carga_motor, acelerador,
                       temp_admision, combustible, voltaje, presion_colector]
                self.csv_writer.writerow(row)
                self.csv_file.flush()
                self.current_size = os.path.getsize(self.current_file)
                if self.current_size >= self.max_size_bytes:
                    self.file_counter += 1
                    self.start_new_file()
                    print(f"📦 Archivo rotado - Tamaño: {self.current_size/1024/1024:.1f}MB")
            except Exception as e:
                print(f"❌ Error logging: {e}")
    def get_status(self):
        size_mb = self.current_size / 1024 / 1024
        return {
            'file': os.path.basename(self.current_file) if self.current_file else "None",
            'size_mb': round(size_mb, 2),
            'progress': round((size_mb / 2.5) * 100, 1)
        }

class HighSpeedOBDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ Dashboard OBD-II ALTA VELOCIDAD + WiFi + Logging")
        self.setGeometry(50, 50, 1600, 1000)
        self.elm327 = OptimizedELM327Connection()
        self.logger = DataLogger(max_size_mb=2.5)
        self.fast_timer = QTimer()
        self.fast_timer.timeout.connect(self.read_fast_data)
        self.slow_timer = QTimer()
        self.slow_timer.timeout.connect(self.read_slow_data)
        self.fast_data_cache = {}
        self.slow_data_cache = {}
        self.vehicle_identifier = None
        self.vehicle_profile = None
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
        # Añadir botón de auto-detección si está disponible
        if VEHICLE_DETECTION_AVAILABLE:
            self.btn_auto_detect = QPushButton("🚗 Auto-Detectar Vehículo")
            self.btn_auto_detect.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
            self.btn_auto_detect.clicked.connect(self.auto_detect_vehicle)
            main_layout.addWidget(self.btn_auto_detect)
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
        group_box = QGroupBox("⚡ Datos Críticos (Actualización Rápida)")
        layout = QGridLayout(group_box)
        self.fast_labels = {}
        fast_pids = ['010C', '010D', '0105', '0104', '0111']
        for i, pid in enumerate(fast_pids):
            info = self.elm327.fast_pids[pid]
            name_label = QLabel(f"{info['name']}:")
            name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
            value_label = QLabel("--")
            value_label.setStyleSheet("""
                font-weight: bold; font-size: 22px; color: #D32F2F;
                border: 3px solid #D32F2F; padding: 12px; 
                background-color: #FFEBEE; min-width: 140px; 
                border-radius: 8px; text-align: center;
            """)
            row = i // 3
            col = (i % 3) * 2
            layout.addWidget(name_label, row, col)
            layout.addWidget(value_label, row, col + 1)
            self.fast_labels[pid] = value_label
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
        # Modo emulador
        if hasattr(self.elm327, 'mode') and self.elm327.mode == "emulator":
            simulated_data = self.elm327.read_fast_data()
            self.fast_data_cache = simulated_data
            for pid, value_label in self.fast_labels.items():
                if pid in simulated_data:
                    info = simulated_data[pid]
                    value_label.setText(f"{info['value']} {info['unit']}")
            self.logger.log_data(self.fast_data_cache, self.slow_data_cache)
            log_status = self.logger.get_status()
            self.logging_status.setText(f"📝 Log: {log_status['file']} ({log_status['size_mb']}MB)")
            return
        data = self.elm327.read_fast_data()
        if data:
            self.fast_data_cache = data
            for pid, value_label in self.fast_labels.items():
                if pid in data:
                    info = data[pid]
                    value_label.setText(f"{info['value']} {info['unit']}")
            self.logger.log_data(self.fast_data_cache, self.slow_data_cache)
            log_status = self.logger.get_status()
            self.logging_status.setText(f"📝 Log: {log_status['file']} ({log_status['size_mb']}MB)")
    def read_slow_data(self):
        # Modo emulador
        if hasattr(self.elm327, 'mode') and self.elm327.mode == "emulator":
            simulated_slow_data = self.elm327.read_slow_data()
            self.slow_data_cache = simulated_slow_data
            for pid, value_label in self.slow_labels.items():
                if pid in simulated_slow_data:
                    info = simulated_slow_data[pid]
                    value_label.setText(f"{info['value']} {info['unit']}")
            return
        data = self.elm327.read_slow_data()
        if data:
            self.slow_data_cache = data
            for pid, value_label in self.slow_labels.items():
                if pid in data:
                    info = data[pid]
                    value_label.setText(f"{info['value']} {info['unit']}")
    def auto_detect_vehicle(self):
        """NUEVA función para detección automática"""
        if not hasattr(self.elm327, 'connected') or not self.elm327.connected:
            QMessageBox.warning(self, "Advertencia", "Primero conecta al ELM327")
            return
        try:
            self.vehicle_identifier = VehicleIdentifier(self.elm327)
            profile = self.vehicle_identifier.detect_vehicle()
            if profile and profile.get("vehicle_id") == "toyota_hilux_2018_diesel":
                self.show_vehicle_detected(profile)
                self.apply_vehicle_settings(profile)
            else:
                QMessageBox.information(self, "Info", "Vehículo no reconocido o no en base de datos")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error en detección: {str(e)}")
    def show_vehicle_detected(self, profile):
        """Muestra información del vehículo detectado"""
        vehicle_info = f"🚗 {profile['identification']['make']} {profile['identification']['model']} {profile['identification']['year']}"
        QMessageBox.information(self, "Vehículo Detectado", vehicle_info)
    def apply_vehicle_settings(self, profile):
        """Aplica configuraciones específicas del vehículo"""
        # Aquí puedes preseleccionar PIDs óptimos, configurar alertas, etc.
        # Ejemplo: mostrar mensaje
        QMessageBox.information(self, "Configuración", "Configuración de PIDs óptimos aplicada para Hilux 2018")

def main():
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
