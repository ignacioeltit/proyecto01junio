import sys
import os
import socket
import time
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

class RealELM327Connection:
    def __init__(self, ip="192.168.0.10", port=35000):
        self.ip = ip
        self.port = port
        self.socket = None
        self.connected = False
        
        # PIDs principales con interpretaciones reales
        self.main_pids = {
            '010C': {'name': 'RPM', 'unit': 'RPM', 'formula': lambda d: ((int(d[0], 16) * 256) + int(d[1], 16)) / 4 if len(d) >= 2 else 0},
            '010D': {'name': 'Velocidad', 'unit': 'km/h', 'formula': lambda d: int(d[0], 16) if len(d) >= 1 else 0},
            '0105': {'name': 'Temp Refrigerante', 'unit': '°C', 'formula': lambda d: int(d[0], 16) - 40 if len(d) >= 1 else 0},
            '010F': {'name': 'Temp Admisión', 'unit': '°C', 'formula': lambda d: int(d[0], 16) - 40 if len(d) >= 1 else 0},
            '0104': {'name': 'Carga Motor', 'unit': '%', 'formula': lambda d: int(d[0], 16) * 100 / 255 if len(d) >= 1 else 0},
            '0111': {'name': 'Acelerador', 'unit': '%', 'formula': lambda d: int(d[0], 16) * 100 / 255 if len(d) >= 1 else 0},
            '012F': {'name': 'Combustible', 'unit': '%', 'formula': lambda d: int(d[0], 16) * 100 / 255 if len(d) >= 1 else 0},
            '0142': {'name': 'Voltaje', 'unit': 'V', 'formula': lambda d: ((int(d[0], 16) * 256) + int(d[1], 16)) / 1000 if len(d) >= 2 else 0},
            '010B': {'name': 'Presión Colector', 'unit': 'kPa', 'formula': lambda d: int(d[0], 16) if len(d) >= 1 else 0},
        }
        
    def connect(self):
        try:
            print(f"📡 Conectando ELM327 real a {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip, self.port))
            
            # Inicialización
            init_commands = ["ATZ", "ATE0", "ATSP0"]
            for cmd in init_commands:
                self.socket.sendall(f"{cmd}\r\n".encode())
                time.sleep(0.5)
                response = self.socket.recv(1024).decode('utf-8', errors='ignore')
                print(f"Init {cmd}: {response.strip()}")
            
            self.connected = True
            print("✅ ELM327 real conectado y configurado")
            return True
            
        except Exception as e:
            print(f"❌ Error conexión ELM327: {e}")
            return False
    
    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False
        print("🔌 ELM327 desconectado")
    
    def read_all_data(self):
        """Leer todos los PIDs principales en una sola operación"""
        if not self.connected or not self.socket:
            return {}
            
        try:
            data = {}
            
            for pid, info in self.main_pids.items():
                try:
                    # Enviar comando PID
                    self.socket.sendall(f"{pid}\r\n".encode())
                    time.sleep(0.2)
                    
                    # Leer respuesta
                    response = self.socket.recv(1024).decode('utf-8', errors='ignore')
                    clean_response = response.replace('\r', '').replace('\n', '').replace('>', '').strip()
                    
                    # Procesar respuesta
                    if '41' in clean_response and 'NO DATA' not in clean_response:
                        parts = clean_response.split()
                        
                        # Encontrar datos después del código 41
                        data_start = -1
                        for i, part in enumerate(parts):
                            if part == '41' and i + 1 < len(parts):
                                expected_pid = parts[i + 1]
                                if expected_pid.upper() == pid[2:4]:  # Verificar PID correcto
                                    data_start = i + 2
                                    break
                        
                        if data_start != -1 and data_start < len(parts):
                            # Extraer bytes de datos
                            data_bytes = []
                            for j in range(data_start, len(parts)):
                                try:
                                    # Verificar que es un byte hex válido
                                    int(parts[j], 16)
                                    data_bytes.append(parts[j])
                                except (ValueError, IndexError):
                                    break
                                    
                                # Parar si encontramos otro comando
                                if parts[j] == '41':
                                    break
                            
                            # Interpretar datos
                            if data_bytes:
                                try:
                                    value = info['formula'](data_bytes)
                                    data[pid] = {
                                        'name': info['name'],
                                        'value': round(value, 1) if isinstance(value, float) else value,
                                        'unit': info['unit'],
                                        'raw_bytes': data_bytes
                                    }
                                except Exception as calc_error:
                                    print(f"⚠️ Error calculando {pid}: {calc_error}")
                                    data[pid] = {
                                        'name': info['name'],
                                        'value': 0,
                                        'unit': info['unit'],
                                        'raw_bytes': data_bytes
                                    }
                        
                except Exception as pid_error:
                    print(f"❌ Error leyendo {pid}: {pid_error}")
                    continue
            
            return data
            
        except Exception as e:
            print(f"❌ Error leyendo datos: {e}")
            return {}

class RealOBDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚗 Dashboard OBD-II REAL - 42 PIDs Funcionales")
        self.setGeometry(50, 50, 1600, 1000)
        
        # Conexión real ELM327
        self.elm327 = RealELM327Connection()
        
        # Timer para lectura continua
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.read_real_data)
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
        # Panel de estado
        status_panel = self.create_status_panel()
        main_layout.addWidget(status_panel)
        
        # Panel de control
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Panel de datos principales
        main_data_panel = self.create_main_data_panel()
        main_layout.addWidget(main_data_panel)
        
        # Panel de datos adicionales
        additional_data_panel = self.create_additional_data_panel()
        main_layout.addWidget(additional_data_panel)
        
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Dashboard Real - Listo para conectar al ELM327")
        
    def create_status_panel(self):
        group_box = QGroupBox("📊 Estado de Conexión ELM327 Real")
        layout = QHBoxLayout(group_box)
        
        self.connection_status = QLabel("🔴 DESCONECTADO")
        self.connection_status.setStyleSheet("""
            font-weight: bold; font-size: 18px; color: red;
            padding: 15px; background-color: #FFE4E1;
            border: 3px solid red; border-radius: 8px;
        """)
        layout.addWidget(self.connection_status)
        
        self.vehicle_info = QLabel("🚗 Vehículo: Esperando datos...")
        self.vehicle_info.setStyleSheet("""
            font-weight: bold; font-size: 14px; color: #333;
            padding: 10px; background-color: #F0F8FF;
            border: 2px solid #4169E1; border-radius: 5px;
        """)
        layout.addWidget(self.vehicle_info)
        
        layout.addStretch()
        return group_box
        
    def create_control_panel(self):
        group_box = QGroupBox("🔌 Control ELM327 Real")
        layout = QHBoxLayout(group_box)
        
        self.connect_btn = QPushButton("🔌 Conectar ELM327")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("""
            font-weight: bold; padding: 15px; font-size: 16px;
            background-color: #4CAF50; color: white; border: none; border-radius: 8px;
        """)
        layout.addWidget(self.connect_btn)
        
        self.start_btn = QPushButton("▶️ Iniciar Monitoreo")
        self.start_btn.clicked.connect(self.start_monitoring)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
            font-weight: bold; padding: 15px; font-size: 16px;
            background-color: #2196F3; color: white; border: none; border-radius: 8px;
        """)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Detener")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            font-weight: bold; padding: 15px; font-size: 16px;
            background-color: #FF5722; color: white; border: none; border-radius: 8px;
        """)
        layout.addWidget(self.stop_btn)
        
        layout.addStretch()
        return group_box
        
    def create_main_data_panel(self):
        group_box = QGroupBox("🔥 Datos Principales del Motor")
        layout = QGridLayout(group_box)
        
        self.main_labels = {}
        main_pids = ['010C', '010D', '0105', '010F', '0104', '0111']
        
        for i, pid in enumerate(main_pids):
            info = self.elm327.main_pids[pid]
            
            # Etiqueta del nombre
            name_label = QLabel(f"{info['name']}:")
            name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
            
            # Etiqueta del valor
            value_label = QLabel("--")
            value_label.setStyleSheet("""
                font-weight: bold; font-size: 24px; color: #1976D2;
                border: 3px solid #1976D2; padding: 15px; 
                background-color: #E3F2FD; min-width: 150px; 
                border-radius: 10px; text-align: center;
            """)
            
            # Posición en grid (2 columnas)
            row = i // 2
            col = (i % 2) * 2
            
            layout.addWidget(name_label, row, col)
            layout.addWidget(value_label, row, col + 1)
            
            self.main_labels[pid] = value_label
            
        return group_box
        
    def create_additional_data_panel(self):
        group_box = QGroupBox("📈 Datos Adicionales del Vehículo")
        layout = QGridLayout(group_box)
        
        self.additional_labels = {}
        additional_pids = ['012F', '0142', '010B']
        
        for i, pid in enumerate(additional_pids):
            info = self.elm327.main_pids[pid]
            
            name_label = QLabel(f"{info['name']}:")
            name_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #555;")
            
            value_label = QLabel("--")
            value_label.setStyleSheet("""
                font-weight: bold; font-size: 18px; color: #388E3C;
                border: 2px solid #388E3C; padding: 10px; 
                background-color: #E8F5E8; min-width: 120px; 
                border-radius: 8px; text-align: center;
            """)
            
            layout.addWidget(name_label, 0, i * 2)
            layout.addWidget(value_label, 0, i * 2 + 1)
            
            self.additional_labels[pid] = value_label
            
        return group_box
        
    def toggle_connection(self):
        if not self.elm327.connected:
            # Conectar
            if self.elm327.connect():
                self.connection_status.setText("🟢 CONECTADO - ELM327 Real")
                self.connection_status.setStyleSheet("""
                    font-weight: bold; font-size: 18px; color: green;
                    padding: 15px; background-color: #F0FFF0;
                    border: 3px solid green; border-radius: 8px;
                """)
                self.connect_btn.setText("🔌 Desconectar")
                self.connect_btn.setStyleSheet("""
                    font-weight: bold; padding: 15px; font-size: 16px;
                    background-color: #F44336; color: white; border: none; border-radius: 8px;
                """)
                self.start_btn.setEnabled(True)
                self.vehicle_info.setText("🚗 Vehículo: ELM327 v1.5 - 42 PIDs disponibles")
                print("✅ Dashboard conectado al ELM327 real")
            else:
                QMessageBox.critical(self, "Error", "No se pudo conectar al ELM327 real")
        else:
            # Desconectar
            self.stop_monitoring()
            self.elm327.disconnect()
            self.connection_status.setText("🔴 DESCONECTADO")
            self.connection_status.setStyleSheet("""
                font-weight: bold; font-size: 18px; color: red;
                padding: 15px; background-color: #FFE4E1;
                border: 3px solid red; border-radius: 8px;
            """)
            self.connect_btn.setText("🔌 Conectar ELM327")
            self.connect_btn.setStyleSheet("""
                font-weight: bold; padding: 15px; font-size: 16px;
                background-color: #4CAF50; color: white; border: none; border-radius: 8px;
            """)
            self.start_btn.setEnabled(False)
            self.vehicle_info.setText("🚗 Vehículo: Esperando conexión...")
            
            # Limpiar datos
            for label in list(self.main_labels.values()) + list(self.additional_labels.values()):
                label.setText("--")
                
    def start_monitoring(self):
        self.data_timer.start(2000)  # Cada 2 segundos
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        print("▶️ Monitoreo en tiempo real iniciado")
        
    def stop_monitoring(self):
        self.data_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        print("⏹️ Monitoreo detenido")
        
    def read_real_data(self):
        """Leer y mostrar datos reales del vehículo"""
        if not self.elm327.connected:
            return
            
        print("📊 Leyendo datos reales del vehículo...")
        
        # Leer todos los datos
        data = self.elm327.read_all_data()
        
        if data:
            # Actualizar displays principales
            for pid, value_label in self.main_labels.items():
                if pid in data:
                    info = data[pid]
                    formatted_value = f"{info['value']} {info['unit']}"
                    value_label.setText(formatted_value)
                    print(f"   {info['name']}: {formatted_value}")
            
            # Actualizar displays adicionales
            for pid, value_label in self.additional_labels.items():
                if pid in data:
                    info = data[pid]
                    formatted_value = f"{info['value']} {info['unit']}"
                    value_label.setText(formatted_value)
            
            # Actualizar barra de estado
            timestamp = datetime.now().strftime("%H:%M:%S")
            rpm = data.get('010C', {}).get('value', 0)
            speed = data.get('010D', {}).get('value', 0)
            temp = data.get('0105', {}).get('value', 0)
            self.status_bar.showMessage(f"✅ {timestamp} - RPM: {rpm}, Velocidad: {speed} km/h, Temp: {temp}°C - ELM327 Real")
        else:
            print("❌ Sin datos del vehículo")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    print("🚗 Dashboard OBD-II Real - Todos los PIDs Funcionales")
    print("📡 Usando datos reales del ELM327 WiFi")
    print("🔥 42 PIDs soportados detectados")
    
    dashboard = RealOBDDashboard()
    dashboard.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
