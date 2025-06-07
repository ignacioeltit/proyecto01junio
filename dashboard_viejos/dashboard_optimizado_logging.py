import sys
import os
import socket
import time
import csv
import threading
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

class OptimizedELM327Connection:
    def __init__(self, ip="192.168.0.10", port=35000):
        self.ip = ip
        self.port = port
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
        }
        
    def connect(self):
        try:
            print(f"📡 Conectando ELM327 optimizado a {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)  # Timeout más corto
            self.socket.connect((self.ip, self.port))
            
            # Configuración optimizada para velocidad
            commands = [
                ("ATZ", 2),      # Reset
                ("ATE0", 0.3),   # Sin eco (crítico para velocidad)
                ("ATL0", 0.3),   # Sin line feeds
                ("ATS0", 0.3),   # Sin espacios
                ("ATH1", 0.3),   # Headers activados
                ("ATSP0", 0.3),  # Protocolo automático
                ("0100", 1)      # Test conectividad OBD
            ]
            
            for cmd, wait in commands:
                self.socket.sendall(f"{cmd}\r".encode())  # Solo \r para velocidad
                time.sleep(wait)
                if wait > 0.5:  # Solo leer respuesta en comandos importantes
                    response = self.socket.recv(512).decode('utf-8', errors='ignore')
                    print(f"   {cmd}: {response.strip()[:30]}...")
            
            self.connected = True
            print("✅ ELM327 optimizado conectado")
            return True
            
        except Exception as e:
            print(f"❌ Error conexión: {e}")
            return False
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False
    
    def read_fast_data(self):
        """Leer solo PIDs críticos para máxima velocidad"""
        if not self.connected or not self.socket:
            return {}
            
        data = {}
        start_time = time.time()
        
        try:
            for pid, info in self.fast_pids.items():
                try:
                    # Enviar comando sin delay
                    self.socket.sendall(f"{pid}\r".encode())
                    time.sleep(0.05)  # Mínimo delay
                    
                    # Leer respuesta con timeout corto
                    self.socket.settimeout(0.5)
                    response = self.socket.recv(256).decode('utf-8', errors='ignore')
                    
                    # Procesamiento rápido
                    if '41' in response and 'NODATA' not in response:
                        parts = response.replace('\r', '').replace('\n', '').replace('>', '').split()
                        
                        # Encontrar datos rápidamente
                        for i, part in enumerate(parts):
                            if part == '41' and i + 1 < len(parts) and parts[i + 1] == pid[2:4]:
                                data_start = i + 2
                                if data_start < len(parts):
                                    # Extraer bytes necesarios
                                    data_bytes = []
                                    for j in range(info['bytes']):
                                        if data_start + j < len(parts):
                                            try:
                                                int(parts[data_start + j], 16)  # Validar hex
                                                data_bytes.append(parts[data_start + j])
                                            except:
                                                break
                                    
                                    # Calcular valor
                                    if len(data_bytes) == info['bytes']:
                                        value = info['formula'](data_bytes)
                                        data[pid] = {
                                            'name': info['name'],
                                            'value': value,
                                            'unit': info['unit']
                                        }
                                break
                        
                except Exception as pid_error:
                    continue  # Skip errores para mantener velocidad
            
            read_time = (time.time() - start_time) * 1000
            if read_time > 100:  # Advertir si es muy lento
                print(f"⚠️ Lectura lenta: {read_time:.0f}ms")
            
            return data
            
        except Exception as e:
            print(f"❌ Error lectura rápida: {e}")
            return {}
    
    def read_slow_data(self):
        """Leer PIDs adicionales menos críticos"""
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

class DataLogger:
    def __init__(self, max_size_mb=2.5):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.current_file = None
        self.file_counter = 1
        self.current_size = 0
        self.csv_writer = None
        self.csv_file = None
        self.lock = threading.Lock()
        
        # Crear carpeta de logs
        self.log_dir = "logs_obd"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.start_new_file()
    
    def start_new_file(self):
        """Iniciar nuevo archivo de log"""
        with self.lock:
            # Cerrar archivo anterior
            if self.csv_file:
                self.csv_file.close()
            
            # Crear nuevo archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"obd_log_{timestamp}_{self.file_counter:03d}.csv"
            filepath = os.path.join(self.log_dir, filename)
            
            self.csv_file = open(filepath, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Header
            header = ['timestamp', 'rpm', 'velocidad', 'temp_motor', 'carga_motor', 
                     'acelerador', 'temp_admision', 'combustible', 'voltaje', 'presion_colector']
            self.csv_writer.writerow(header)
            self.csv_file.flush()
            
            self.current_size = 0
            self.current_file = filepath
            print(f"📝 Nuevo log iniciado: {filename}")
    
    def log_data(self, fast_data, slow_data):
        """Registrar datos en CSV"""
        with self.lock:
            try:
                # Preparar datos
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                
                # Extraer valores con defaults
                rpm = fast_data.get('010C', {}).get('value', 0)
                velocidad = fast_data.get('010D', {}).get('value', 0)
                temp_motor = fast_data.get('0105', {}).get('value', 0)
                carga_motor = fast_data.get('0104', {}).get('value', 0)
                acelerador = fast_data.get('0111', {}).get('value', 0)
                
                temp_admision = slow_data.get('010F', {}).get('value', 0)
                combustible = slow_data.get('012F', {}).get('value', 0)
                voltaje = slow_data.get('0142', {}).get('value', 0)
                presion_colector = slow_data.get('010B', {}).get('value', 0)
                
                # Escribir fila
                row = [timestamp, rpm, velocidad, temp_motor, carga_motor, acelerador,
                       temp_admision, combustible, voltaje, presion_colector]
                
                self.csv_writer.writerow(row)
                self.csv_file.flush()
                
                # Actualizar tamaño
                self.current_size = os.path.getsize(self.current_file)
                
                # Verificar límite de tamaño
                if self.current_size >= self.max_size_bytes:
                    self.file_counter += 1
                    self.start_new_file()
                    print(f"📦 Archivo rotado - Tamaño: {self.current_size/1024/1024:.1f}MB")
                
            except Exception as e:
                print(f"❌ Error logging: {e}")
    
    def get_status(self):
        """Obtener estado del logging"""
        size_mb = self.current_size / 1024 / 1024
        return {
            'file': os.path.basename(self.current_file) if self.current_file else "None",
            'size_mb': round(size_mb, 2),
            'progress': round((size_mb / 2.5) * 100, 1)
        }

class HighSpeedOBDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚡ Dashboard OBD-II ALTA VELOCIDAD + Logging Automático")
        self.setGeometry(50, 50, 1600, 1000)
        
        # Conexión optimizada
        self.elm327 = OptimizedELM327Connection()
        
        # Logger automático
        self.logger = DataLogger(max_size_mb=2.5)
        
        # Timers separados para velocidad
        self.fast_timer = QTimer()  # Datos críticos
        self.fast_timer.timeout.connect(self.read_fast_data)
        
        self.slow_timer = QTimer()  # Datos adicionales
        self.slow_timer.timeout.connect(self.read_slow_data)
        
        # Cache de datos
        self.fast_data_cache = {}
        self.slow_data_cache = {}
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Panel de estado con logging
        status_panel = self.create_status_panel()
        main_layout.addWidget(status_panel)
        
        # Panel de control optimizado
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Panel de datos críticos (actualización rápida)
        fast_data_panel = self.create_fast_data_panel()
        main_layout.addWidget(fast_data_panel)
        
        # Panel de datos adicionales (actualización lenta)
        slow_data_panel = self.create_slow_data_panel()
        main_layout.addWidget(slow_data_panel)
        
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Dashboard Alta Velocidad - Listo")
        
    def create_status_panel(self):
        group_box = QGroupBox("⚡ Estado del Sistema")
        layout = QHBoxLayout(group_box)
        
        # Estado conexión
        self.connection_status = QLabel("🔴 DESCONECTADO")
        self.connection_status.setStyleSheet("""
            font-weight: bold; font-size: 16px; color: red;
            padding: 10px; background-color: #FFE4E1;
            border: 2px solid red; border-radius: 5px;
        """)
        layout.addWidget(self.connection_status)
        
        # Estado logging
        self.logging_status = QLabel("📝 Logging: Inactivo")
        self.logging_status.setStyleSheet("""
            font-weight: bold; font-size: 14px; color: #555;
            padding: 10px; background-color: #F0F8FF;
            border: 2px solid #4169E1; border-radius: 5px;
        """)
        layout.addWidget(self.logging_status)
        
        # Velocidad de datos
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
        
        self.connect_btn = QPushButton("🔌 Conectar")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("""
            font-weight: bold; padding: 12px; font-size: 14px;
            background-color: #4CAF50; color: white; border: none; border-radius: 6px;
        """)
        layout.addWidget(self.connect_btn)
        
        # Velocidad crítica
        self.start_fast_btn = QPushButton("⚡ Modo Rápido (5Hz)")
        self.start_fast_btn.clicked.connect(self.start_fast_mode)
        self.start_fast_btn.setEnabled(False)
        self.start_fast_btn.setStyleSheet("""
            font-weight: bold; padding: 12px; font-size: 14px;
            background-color: #FF5722; color: white; border: none; border-radius: 6px;
        """)
        layout.addWidget(self.start_fast_btn)
        
        # Velocidad normal
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
        """Modo alta velocidad: 5 Hz datos críticos + 0.5 Hz datos adicionales"""
        self.fast_timer.start(200)    # 5 Hz = 200ms
        self.slow_timer.start(2000)   # 0.5 Hz = 2000ms
        
        self.start_fast_btn.setEnabled(False)
        self.start_normal_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.speed_status.setText("⚡ Velocidad: 5 Hz (Ultra Rápido)")
        print("⚡ Modo alta velocidad activado: 5 Hz")
        
    def start_normal_mode(self):
        """Modo normal: 2 Hz datos críticos + 0.5 Hz datos adicionales"""
        self.fast_timer.start(500)    # 2 Hz = 500ms
        self.slow_timer.start(2000)   # 0.5 Hz = 2000ms
        
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
        """Leer datos críticos (alta frecuencia)"""
        data = self.elm327.read_fast_data()
        if data:
            self.fast_data_cache = data
            
            # Actualizar UI
            for pid, value_label in self.fast_labels.items():
                if pid in data:
                    info = data[pid]
                    value_label.setText(f"{info['value']} {info['unit']}")
            
            # Log completo (con datos lentos si existen)
            self.logger.log_data(self.fast_data_cache, self.slow_data_cache)
            
            # Actualizar estado logging
            log_status = self.logger.get_status()
            self.logging_status.setText(f"📝 Log: {log_status['file']} ({log_status['size_mb']}MB)")
        
    def read_slow_data(self):
        """Leer datos adicionales (baja frecuencia)"""
        data = self.elm327.read_slow_data()
        if data:
            self.slow_data_cache = data
            
            # Actualizar UI
            for pid, value_label in self.slow_labels.items():
                if pid in data:
                    info = data[pid]
                    value_label.setText(f"{info['value']} {info['unit']}")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    print("⚡ Dashboard OBD-II Alta Velocidad + Logging Automático")
    print("🚀 Optimizado para velocidad máxima")
    print("📝 Logging automático < 2.5MB por archivo")
    
    dashboard = HighSpeedOBDDashboard()
    dashboard.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()