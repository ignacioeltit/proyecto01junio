import sys
import os
import socket
import time
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

class DirectELM327Connection:
    def __init__(self, ip="192.168.0.10", port=35000):
        self.ip = ip
        self.port = port
        self.socket = None
        self.connected = False
        
    def connect(self):
        try:
            print(f"📡 Conectando ELM327 directo a {self.ip}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip, self.port))
            
            # Inicialización ELM327
            init_commands = ["ATZ", "ATE0", "ATSP0"]
            for cmd in init_commands:
                self.socket.sendall(f"{cmd}\r\n".encode())
                time.sleep(0.5)
                response = self.socket.recv(1024).decode('utf-8', errors='ignore')
                print(f"Init {cmd}: {response.strip()}")
            
            self.connected = True
            print("✅ ELM327 inicializado correctamente")
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
    
    def read_pid(self, pid):
        if not self.connected or not self.socket:
            return None
            
        try:
            # Enviar comando PID
            self.socket.sendall(f"{pid}\r\n".encode())
            time.sleep(0.3)
            
            # Leer respuesta
            response = self.socket.recv(1024).decode('utf-8', errors='ignore')
            clean_response = response.replace('\r', '').replace('\n', '').replace('>', '').strip()
            
            print(f"📡 {pid} → {clean_response}")
            
            # Parsear respuesta OBD-II
            if '41' in clean_response and len(clean_response) >= 8:
                # Encontrar la parte de datos después de "41 XX"
                parts = clean_response.split()
                if len(parts) >= 3:
                    if pid == "010C":  # RPM
                        try:
                            a = int(parts[2], 16)
                            b = int(parts[3], 16) if len(parts) > 3 else 0
                            rpm = ((a * 256) + b) / 4
                            return int(rpm)
                        except:
                            return 0
                            
                    elif pid == "010D":  # Velocidad
                        try:
                            speed = int(parts[2], 16)
                            return speed
                        except:
                            return 0
                            
                    elif pid == "0105":  # Temperatura
                        try:
                            temp = int(parts[2], 16) - 40
                            return temp
                        except:
                            return 0
                            
                    elif pid == "0111":  # Throttle
                        try:
                            throttle = int(parts[2], 16) * 100 / 255
                            return int(throttle)
                        except:
                            return 0
            
            return 0
            
        except Exception as e:
            print(f"❌ Error leyendo {pid}: {e}")
            return 0

class DirectOBDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard OBD-II - CONEXIÓN DIRECTA ELM327 WiFi")
        self.setGeometry(100, 100, 1200, 800)
        
        # Conexión directa ELM327
        self.elm327 = DirectELM327Connection()
        
        # Timer para lectura
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.read_real_data)
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Panel de estado
        status_panel = QGroupBox("🚗 Estado de Conexión ELM327 WiFi")
        status_layout = QHBoxLayout(status_panel)
        
        self.connection_status = QLabel("🔴 DESCONECTADO")
        self.connection_status.setStyleSheet("""
            font-weight: bold; font-size: 16px; color: red;
            padding: 10px; background-color: #FFE4E1;
            border: 2px solid red; border-radius: 5px;
        """)
        status_layout.addWidget(self.connection_status)
        
        status_layout.addStretch()
        layout.addWidget(status_panel)
        
        # Panel de control
        control_panel = QGroupBox("🔌 Control Directo")
        control_layout = QHBoxLayout(control_panel)
        
        self.connect_btn = QPushButton("🔌 Conectar ELM327")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("font-weight: bold; padding: 10px; font-size: 14px;")
        control_layout.addWidget(self.connect_btn)
        
        self.start_btn = QPushButton("▶️ Leer Datos")
        self.start_btn.clicked.connect(self.start_reading)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("font-weight: bold; padding: 10px; font-size: 14px;")
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Detener")
        self.stop_btn.clicked.connect(self.stop_reading)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("font-weight: bold; padding: 10px; font-size: 14px;")
        control_layout.addWidget(self.stop_btn)
        
        control_layout.addStretch()
        layout.addWidget(control_panel)
        
        # Panel de datos
        data_panel = self.create_data_panel()
        layout.addWidget(data_panel)
        
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Dashboard directo ELM327 - Listo para conectar")
        
    def create_data_panel(self):
        group_box = QGroupBox("📊 Datos REALES del Vehículo (ELM327 WiFi)")
        layout = QGridLayout(group_box)
        
        self.data_labels = {}
        data_items = [
            ('RPM', '010C'),
            ('Velocidad (km/h)', '010D'), 
            ('Temperatura (°C)', '0105'),
            ('Throttle (%)', '0111')
        ]
        
        for i, (display_name, pid) in enumerate(data_items):
            # Etiqueta
            label = QLabel(f"{display_name}:")
            label.setStyleSheet("font-weight: bold; font-size: 14px;")
            
            # Valor
            value_label = QLabel("--")
            value_label.setStyleSheet("""
                font-weight: bold; font-size: 20px; color: #2E8B57;
                border: 3px solid #2E8B57; padding: 15px; 
                background-color: #F0FFF0; min-width: 150px; 
                border-radius: 8px; text-align: center;
            """)
            
            # Posición en grid
            row = i // 2
            col = (i % 2) * 2
            
            layout.addWidget(label, row, col)
            layout.addWidget(value_label, row, col + 1)
            
            self.data_labels[pid] = value_label
            
        return group_box
        
    def toggle_connection(self):
        if not self.elm327.connected:
            # Conectar
            if self.elm327.connect():
                self.connection_status.setText("🟢 CONECTADO - ELM327 WiFi")
                self.connection_status.setStyleSheet("""
                    font-weight: bold; font-size: 16px; color: green;
                    padding: 10px; background-color: #F0FFF0;
                    border: 2px solid green; border-radius: 5px;
                """)
                self.connect_btn.setText("🔌 Desconectar")
                self.start_btn.setEnabled(True)
                print("✅ Dashboard conectado a ELM327")
            else:
                QMessageBox.critical(self, "Error", "No se pudo conectar al ELM327")
        else:
            # Desconectar
            self.stop_reading()
            self.elm327.disconnect()
            self.connection_status.setText("🔴 DESCONECTADO")
            self.connection_status.setStyleSheet("""
                font-weight: bold; font-size: 16px; color: red;
                padding: 10px; background-color: #FFE4E1;
                border: 2px solid red; border-radius: 5px;
            """)
            self.connect_btn.setText("🔌 Conectar ELM327")
            self.start_btn.setEnabled(False)
            
            # Limpiar datos
            for label in self.data_labels.values():
                label.setText("--")
                
    def start_reading(self):
        self.data_timer.start(2000)  # Cada 2 segundos
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        print("▶️ Iniciando lectura de datos reales...")
        
    def stop_reading(self):
        self.data_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        print("⏹️ Lectura detenida")
        
    def read_real_data(self):
        """Leer datos reales del ELM327"""
        if not self.elm327.connected:
            return
            
        print("📊 Leyendo datos del vehículo...")
        
        # Leer cada PID
        pids_to_read = ['010C', '010D', '0105', '0111']
        
        for pid in pids_to_read:
            value = self.elm327.read_pid(pid)
            if value is not None:
                # Formatear según el tipo
                if pid == '010C':  # RPM
                    formatted_value = f"{value:,} RPM"
                elif pid == '010D':  # Velocidad
                    formatted_value = f"{value} km/h"
                elif pid == '0105':  # Temperatura
                    formatted_value = f"{value}°C"
                elif pid == '0111':  # Throttle
                    formatted_value = f"{value}%"
                else:
                    formatted_value = str(value)
                
                # Actualizar UI
                if pid in self.data_labels:
                    self.data_labels[pid].setText(formatted_value)
                    
        # Actualizar status bar
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_bar.showMessage(f"✅ Datos actualizados: {timestamp} - ELM327 WiFi funcionando")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    print("🚀 Dashboard OBD-II - CONEXIÓN DIRECTA ELM327")
    print("📡 Usando exactamente el mismo código que funciona en la prueba")
    
    dashboard = DirectOBDDashboard()
    dashboard.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
