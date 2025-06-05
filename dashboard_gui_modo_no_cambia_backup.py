import sys
import os
import json
import logging
import socket
import time
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Agregar el directorio src al path si existe
if os.path.exists('src'):
    sys.path.append('src')

try:
    from src.obd.connection import OBDConnection
    from src.obd.emulador import EmuladorOBD
    from src.utils.logging_app import setup_logging
except ImportError:
    print("Usando implementaciones básicas...")
    
    class OBDConnection:
        def __init__(self, mode="usb", port=None, baudrate=38400, ip=None, tcp_port=None, timeout=2):
            self.mode = mode
            self.port = port
            self.baudrate = baudrate
            self.ip = ip
            self.tcp_port = tcp_port
            self.timeout = timeout
            self.connection = None
            
        def connect(self):
            try:
                if self.mode == "wifi":
                    print(f"🔌 Intentando conectar WiFi a {self.ip}:{self.tcp_port}")
                    self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.connection.settimeout(self.timeout)
                    self.connection.connect((self.ip, self.tcp_port))
                    print(f"✅ Conexión WiFi establecida a {self.ip}:{self.tcp_port}")
                    return self.connection
                else:
                    raise ValueError("Modo no soportado en implementación básica")
            except Exception as e:
                print(f"❌ Error conexión WiFi: {e}")
                return None
                
        def disconnect(self):
            if self.connection:
                self.connection.close()
                self.connection = None
                
        def read_data(self, pids):
            # Simulación para pruebas
            import random
            return {pid: random.randint(0, 100) for pid in pids}
    
    class EmuladorOBD:
        def __init__(self):
            pass
        def get_simulated_data(self, pids):
            import random
            data = {}
            for pid in pids:
                if pid == 'rpm':
                    data[pid] = random.randint(800, 3000)
                elif pid == 'vel':
                    data[pid] = random.randint(0, 120)
                elif pid == 'temp':
                    data[pid] = random.randint(70, 95)
                elif pid == 'maf':
                    data[pid] = round(random.uniform(1.0, 5.0), 2)
                elif pid == 'throttle':
                    data[pid] = random.randint(0, 100)
                elif pid == 'volt_bateria':
                    data[pid] = round(random.uniform(13.0, 14.5), 2)
                else:
                    data[pid] = random.randint(0, 100)
            return data
    
    def setup_logging():
        logging.basicConfig(level=logging.INFO)

class WiFiDiagnosticDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Diagnóstico WiFi ELM327")
        self.setGeometry(200, 200, 600, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Texto de resultados
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        # Botones
        buttons_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("🔍 Escanear WiFi")
        self.scan_btn.clicked.connect(self.scan_wifi_networks)
        buttons_layout.addWidget(self.scan_btn)
        
        self.test_ips_btn = QPushButton("🌐 Probar IPs Comunes")
        self.test_ips_btn.clicked.connect(self.test_common_ips)
        buttons_layout.addWidget(self.test_ips_btn)
        
        self.close_btn = QPushButton("Cerrar")
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
    def log_result(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.results_text.append(f"[{timestamp}] {message}")
        
    def scan_wifi_networks(self):
        self.log_result("🔍 Escaneando redes WiFi...")
        try:
            import subprocess
            result = subprocess.run(['netsh', 'wlan', 'show', 'networks'], 
                                  capture_output=True, text=True)
            
            networks = []
            elm327_networks = []
            
            for line in result.stdout.split('\n'):
                if 'SSID' in line and 'All User Profile' not in line:
                    network = line.split(':')[1].strip()
                    networks.append(network)
                    if any(keyword in network.lower() for keyword in 
                          ['elm327', 'obd', 'wifi', 'car', 'auto']):
                        elm327_networks.append(network)
            
            self.log_result(f"✅ Encontradas {len(networks)} redes WiFi")
            for network in networks[:10]:  # Mostrar primeras 10
                self.log_result(f"   📡 {network}")
                
            if elm327_networks:
                self.log_result(f"🎯 Candidatos ELM327: {elm327_networks}")
            else:
                self.log_result("⚠️ No se detectaron redes con nombres típicos de ELM327")
                
        except Exception as e:
            self.log_result(f"❌ Error escaneando WiFi: {e}")
    
    def test_common_ips(self):
        common_configs = [
            ('192.168.0.10', 35000),
            ('192.168.4.1', 35000),
            ('192.168.1.10', 35000),
            ('10.0.0.10', 35000),
            ('192.168.0.10', 23),
            ('192.168.4.1', 23)
        ]
        
        self.log_result("🌐 Probando IPs y puertos comunes de ELM327...")
        
        for ip, port in common_configs:
            try:
                self.log_result(f"   Probando {ip}:{port}...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((ip, port))
                
                if result == 0:
                    self.log_result(f"   ✅ ÉXITO: {ip}:{port} responde!")
                    # Probar comando básico
                    try:
                        sock.sendall(b'ATI\r\n')
                        time.sleep(1)
                        response = sock.recv(1024).decode('utf-8', errors='ignore')
                        self.log_result(f"   📝 Respuesta: {response.strip()}")
                    except:
                        pass
                else:
                    self.log_result(f"   ❌ Sin respuesta: {ip}:{port}")
                    
                sock.close()
                
            except Exception as e:
                self.log_result(f"   💥 Error {ip}:{port}: {e}")

class OBDDataSource(QObject):
    data_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.connection = None
        self.emulator = None
        self.connection_mode = "emulator"
        self.selected_pids = []
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
        # Parámetros de conexión
        self.usb_port = "COM3"
        self.wifi_ip = "192.168.0.10"
        self.wifi_port = 35000
        
        # Mapeo PIDs
        self.pid_mapping = {
            'hex_to_name': {
                '010C': 'rpm', '010D': 'vel', '0105': 'temp',
                '0111': 'throttle', '0110': 'maf', '0142': 'volt_bateria'
            },
            'name_to_hex': {
                'rpm': '010C', 'vel': '010D', 'temp': '0105',
                'throttle': '0111', 'maf': '0110', 'volt_bateria': '0142'
            }
        }
        
        try:
            setup_logging()
        except:
            logging.basicConfig(level=logging.INFO)
    
    def set_connection_mode(self, mode, **params):
        self.connection_mode = mode
        
        if mode == "usb" and "port" in params:
            self.usb_port = params["port"]
        elif mode == "wifi":
            if "ip" in params:
                self.wifi_ip = params["ip"]
            if "port" in params:
                self.wifi_port = params["port"]
                
        print(f"🔧 Modo configurado: {mode}")
        if mode == "wifi":
            print(f"📡 WiFi: {self.wifi_ip}:{self.wifi_port}")
    
    def connect(self):
        print(f"🔌 Intentando conectar en modo: {self.connection_mode}")
        
        try:
            if self.connection_mode == "emulator":
                self.emulator = EmuladorOBD()
                self.is_connected = True
                self.status_changed.emit("Conectado (Emulador)")
                print("✅ Conexión emulador establecida")
                return True
                
            elif self.connection_mode == "wifi":
                print(f"📡 Conectando WiFi a {self.wifi_ip}:{self.wifi_port}...")
                
                # Verificar conectividad básica primero
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(5)
                test_result = test_sock.connect_ex((self.wifi_ip, self.wifi_port))
                test_sock.close()
                
                if test_result != 0:
                    error_msg = f"❌ No se puede conectar a {self.wifi_ip}:{self.wifi_port}"
                    print(error_msg)
                    self.status_changed.emit(error_msg)
                    return False
                
                # Si la conexión básica funciona, crear conexión OBD
                self.connection = OBDConnection(
                    mode="wifi", 
                    ip=self.wifi_ip, 
                    tcp_port=self.wifi_port,
                    timeout=5
                )
                
                if self.connection.connect():
                    self.is_connected = True
                    success_msg = f"✅ Conectado (WiFi {self.wifi_ip}:{self.wifi_port})"
                    self.status_changed.emit(success_msg)
                    print(success_msg)
                    return True
                else:
                    error_msg = "❌ Conexión OBD WiFi falló"
                    self.status_changed.emit(error_msg)
                    print(error_msg)
                    return False
                    
        except Exception as e:
            error_msg = f"💥 Error en conexión: {e}"
            print(error_msg)
            self.status_changed.emit(error_msg)
            return False
    
    def disconnect(self):
        try:
            if self.connection:
                self.connection.disconnect()
            self.is_connected = False
            self.status_changed.emit("Desconectado")
            print("🔌 Conexión terminada")
        except Exception as e:
            print(f"❌ Error al desconectar: {e}")
    
    def set_selected_pids(self, pids):
        self.selected_pids = pids[:8]
        print(f"📋 PIDs seleccionados: {self.selected_pids}")
    
    def read_data(self):
        if not self.is_connected:
            return {}
        
        try:
            if self.connection_mode == "emulator" and self.emulator:
                # Convertir hex a nombres
                emulator_pids = []
                for pid in self.selected_pids:
                    if pid in self.pid_mapping['hex_to_name']:
                        emulator_pids.append(self.pid_mapping['hex_to_name'][pid])
                    else:
                        emulator_pids.append(pid)
                
                emulator_data = self.emulator.get_simulated_data(emulator_pids)
                
                # Convertir de vuelta a hex
                data = {}
                for name, value in emulator_data.items():
                    if name in self.pid_mapping['name_to_hex']:
                        hex_pid = self.pid_mapping['name_to_hex'][name]
                        data[hex_pid] = value
                        data[name] = value  # Mantener ambos
                    else:
                        data[name] = value
                
            elif self.connection_mode == "wifi" and self.connection:
                data = self.connection.read_data(self.selected_pids)
            else:
                data = {}
            
            if data:
                self.data_received.emit(data)
            
            return data
            
        except Exception as e:
            print(f"❌ Error leyendo datos: {e}")
            return {}
    
    def get_connection_status(self):
        return self.is_connected

class OBDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard OBD-II - Diagnóstico WiFi Avanzado")
        self.setGeometry(100, 100, 1400, 900)
        
        self.data_source = OBDDataSource()
        self.data_source.data_received.connect(self.update_display)
        self.data_source.status_changed.connect(self.update_status)
        
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.read_data)
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        data_panel = self.create_data_panel()
        layout.addWidget(data_panel)
        
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Desconectado - Dashboard con diagnóstico WiFi")
        
    def create_control_panel(self):
        group_box = QGroupBox("🔌 Control de Conexión OBD-II (con Diagnóstico WiFi)")
        layout = QVBoxLayout(group_box)
        
        # Modo
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Modo:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Emulador", "WiFi ELM327"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        
        layout.addLayout(mode_layout)
        
        # Configuración WiFi
        wifi_layout = QHBoxLayout()
        wifi_layout.addWidget(QLabel("📡 IP ELM327:"))
        
        self.wifi_ip_input = QLineEdit("192.168.0.10")
        wifi_layout.addWidget(self.wifi_ip_input)
        
        wifi_layout.addWidget(QLabel("Puerto:"))
        self.wifi_port_input = QLineEdit("35000")
        self.wifi_port_input.setMaximumWidth(80)
        wifi_layout.addWidget(self.wifi_port_input)
        
        # Botón diagnóstico
        self.diagnostic_btn = QPushButton("🔍 Diagnóstico WiFi")
        self.diagnostic_btn.clicked.connect(self.open_wifi_diagnostic)
        wifi_layout.addWidget(self.diagnostic_btn)
        
        wifi_layout.addStretch()
        layout.addLayout(wifi_layout)
        
        # Botones de control
        buttons_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("🔌 Conectar")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        
        self.start_btn = QPushButton("▶️ Iniciar Lectura")
        self.start_btn.clicked.connect(self.start_reading)
        self.start_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("⏹️ Detener")
        self.stop_btn.clicked.connect(self.stop_reading)
        self.stop_btn.setEnabled(False)
        
        buttons_layout.addWidget(self.connect_btn)
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        return group_box
        
    def create_data_panel(self):
        group_box = QGroupBox("📊 Datos OBD-II en Tiempo Real")
        layout = QGridLayout(group_box)
        
        self.data_labels = {}
        pids = [
            ('RPM', '010C'), ('Velocidad (km/h)', '010D'), 
            ('Temperatura (°C)', '0105'), ('MAF (g/s)', '0110'),
            ('Throttle (%)', '0111'), ('Voltaje Batería (V)', '0142')
        ]
        
        for i, (display_name, pid) in enumerate(pids):
            label = QLabel(f"{display_name}:")
            label.setStyleSheet("font-weight: bold;")
            
            value_label = QLabel("--")
            value_label.setStyleSheet("""
                font-weight: bold; font-size: 16px; color: #2E8B57;
                border: 2px solid #ccc; padding: 8px; background-color: #f0f0f0;
                min-width: 120px; border-radius: 5px;
            """)
            
            row = i // 2
            col = (i % 2) * 2
            
            layout.addWidget(label, row, col)
            layout.addWidget(value_label, row, col + 1)
            
            self.data_labels[pid] = value_label
            
        return group_box
    
    def open_wifi_diagnostic(self):
        dialog = WiFiDiagnosticDialog(self)
        dialog.exec()
        
    def on_mode_changed(self, mode):
        self.status_bar.showMessage(f"Modo {mode} seleccionado")
        
    def toggle_connection(self):
        if not self.data_source.get_connection_status():
            mode = self.mode_combo.currentText()
            
            if mode == "Emulador":
                self.data_source.set_connection_mode("emulator")
            elif mode == "WiFi ELM327":
                ip = self.wifi_ip_input.text()
                port = int(self.wifi_port_input.text())
                self.data_source.set_connection_mode("wifi", ip=ip, port=port)
            
            if self.data_source.connect():
                self.connect_btn.setText("🔌 Desconectar")
                self.start_btn.setEnabled(True)
                default_pids = ['010C', '010D', '0105', '0110', '0111', '0142']
                self.data_source.set_selected_pids(default_pids)
        else:
            self.stop_reading()
            self.data_source.disconnect()
            self.connect_btn.setText("🔌 Conectar")
            self.start_btn.setEnabled(False)
            for label in self.data_labels.values():
                label.setText("--")
            
    def start_reading(self):
        self.data_timer.start(1000)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
    def stop_reading(self):
        self.data_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
    def read_data(self):
        self.data_source.read_data()
        
    def update_display(self, data):
        for pid, value in data.items():
            if pid in self.data_labels:
                if pid == '010C':
                    formatted_value = f"{value:,} RPM"
                elif pid == '010D':
                    formatted_value = f"{value} km/h"
                elif pid == '0105':
                    formatted_value = f"{value}°C"
                elif pid == '0110':
                    formatted_value = f"{value} g/s"
                elif pid == '0111':
                    formatted_value = f"{value}%"
                elif pid == '0142':
                    formatted_value = f"{value}V"
                else:
                    formatted_value = str(value)
                    
                self.data_labels[pid].setText(formatted_value)
                
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_bar.showMessage(f"Última actualización: {timestamp}")
                    
    def update_status(self, status):
        self.status_bar.showMessage(status)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    try:
        setup_logging()
    except:
        logging.basicConfig(level=logging.INFO)
    
    print("🚀 Dashboard OBD-II con Diagnóstico WiFi Avanzado")
    print("🔍 Usa 'Diagnóstico WiFi' para encontrar tu ELM327")
    
    dashboard = OBDDashboard()
    dashboard.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
