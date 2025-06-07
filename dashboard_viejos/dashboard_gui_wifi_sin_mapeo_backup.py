import sys
import os
import json
import logging
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Agregar el directorio src al path si existe
if os.path.exists('src'):
    sys.path.append('src')

try:
    from src.obd.connection import OBDConnection
    from src.obd.emulador import EmuladorOBD, emular_datos_obd2
    from src.utils.logging_app import setup_logging
except ImportError:
    try:
        from obd.connection import OBDConnection
        from obd.emulador import EmuladorOBD, emular_datos_obd2
        from utils.logging_app import setup_logging
    except ImportError:
        print("Usando implementaciones básicas...")
        
        import socket
        import serial
        
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
                    if self.mode == "usb":
                        self.connection = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
                    elif self.mode == "wifi":
                        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.connection.settimeout(self.timeout)
                        self.connection.connect((self.ip, self.tcp_port))
                    else:
                        raise ValueError("Modo de conexión no soportado")
                    return self.connection
                except Exception as e:
                    print(f"Error en conexión OBD: {e}")
                    return None
                    
            def disconnect(self):
                if self.connection:
                    self.connection.close()
                    self.connection = None
                    
            def write(self, data):
                if self.mode == "usb":
                    self.connection.write(data.encode())
                elif self.mode == "wifi":
                    self.connection.sendall(data.encode())
                    
            def read(self, size=128):
                if self.mode == "usb":
                    return self.connection.read(size).decode(errors="ignore")
                elif self.mode == "wifi":
                    return self.connection.recv(size).decode(errors="ignore")
                    
            def read_data(self, pids):
                # Implementación básica para pruebas
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
        
        def emular_datos_obd2(escenarios=None, pids=None, registros_por_fase=1):
            if pids is None:
                pids = ['rpm', 'vel', 'temp']
            emulador = EmuladorOBD()
            return [emulador.get_simulated_data(pids)]
        
        def setup_logging():
            logging.basicConfig(level=logging.INFO)

class OBDDataSource(QObject):
    data_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.connection = None
        self.emulator = None
        self.connection_mode = "emulator"  # emulator, usb, wifi
        self.selected_pids = []
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
        # Parámetros de conexión
        self.usb_port = "COM3"
        self.wifi_ip = "192.168.0.10"
        self.wifi_port = 35000
        
        try:
            setup_logging()
        except:
            logging.basicConfig(level=logging.INFO)
    
    def set_connection_mode(self, mode, **params):
        """Configurar modo de conexión: emulator, usb, wifi"""
        self.connection_mode = mode
        
        if mode == "usb" and "port" in params:
            self.usb_port = params["port"]
        elif mode == "wifi":
            if "ip" in params:
                self.wifi_ip = params["ip"]
            if "port" in params:
                self.wifi_port = params["port"]
                
        self.logger.info(f"Modo configurado: {mode}")
    
    def connect(self):
        """Establece conexión según el modo configurado"""
        try:
            if self.connection_mode == "emulator":
                self.emulator = EmuladorOBD()
                self.is_connected = True
                self.status_changed.emit("Conectado (Emulador)")
                self.logger.info("Conexión establecida en modo emulador")
                return True
                
            elif self.connection_mode == "usb":
                self.connection = OBDConnection(mode="usb", port=self.usb_port)
                if self.connection.connect():
                    self.is_connected = True
                    self.status_changed.emit(f"Conectado (USB {self.usb_port})")
                    self.logger.info(f"Conexión USB establecida en {self.usb_port}")
                    return True
                else:
                    self.status_changed.emit("Error conexión USB")
                    return False
                    
            elif self.connection_mode == "wifi":
                self.connection = OBDConnection(
                    mode="wifi", 
                    ip=self.wifi_ip, 
                    tcp_port=self.wifi_port,
                    timeout=5
                )
                if self.connection.connect():
                    self.is_connected = True
                    self.status_changed.emit(f"Conectado (WiFi {self.wifi_ip}:{self.wifi_port})")
                    self.logger.info(f"Conexión WiFi establecida en {self.wifi_ip}:{self.wifi_port}")
                    return True
                else:
                    self.status_changed.emit("Error conexión WiFi")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error en conexión: {e}")
            self.status_changed.emit(f"Error: {str(e)}")
            return False
    
    def disconnect(self):
        """Desconecta la conexión"""
        try:
            if self.connection:
                self.connection.disconnect()
            self.is_connected = False
            self.status_changed.emit("Desconectado")
            self.logger.info("Conexión terminada")
        except Exception as e:
            self.logger.error(f"Error al desconectar: {e}")
    
    def set_selected_pids(self, pids):
        """Configura los PIDs a monitorear"""
        self.selected_pids = pids[:8]
        self.logger.info(f"PIDs seleccionados: {self.selected_pids}")
    
    def read_data(self):
        """Lee datos según el modo de conexión"""
        if not self.is_connected:
            return {}
        
        try:
            if self.connection_mode == "emulator" and self.emulator:
                data = self.emulator.get_simulated_data(self.selected_pids)
            elif self.connection_mode in ["usb", "wifi"] and self.connection:
                data = self.connection.read_data(self.selected_pids)
            else:
                data = {}
            
            if data:
                self.data_received.emit(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error leyendo datos: {e}")
            return {}
    
    def get_connection_status(self):
        return self.is_connected
    
    def get_available_pids(self):
        return ['rpm', 'vel', 'temp', 'maf', 'throttle', 'volt_bateria']

class OBDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard OBD-II - WiFi/USB/Emulador")
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
        
        # Panel de control mejorado
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        # Panel de datos
        data_panel = self.create_data_panel()
        layout.addWidget(data_panel)
        
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Desconectado - Selecciona modo de conexión")
        
    def create_control_panel(self):
        """Crear panel de controles con soporte WiFi/USB/Emulador"""
        group_box = QGroupBox("🔌 Control de Conexión OBD-II (WiFi/USB/Emulador)")
        layout = QVBoxLayout(group_box)
        
        # Fila 1: Modo de conexión
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Modo:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Emulador", "WiFi ELM327", "USB/Serial"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        
        layout.addLayout(mode_layout)
        
        # Fila 2: Configuración específica por modo
        self.config_stack = QStackedWidget()
        
        # Widget para emulador
        emulator_widget = QWidget()
        emulator_layout = QHBoxLayout(emulator_widget)
        emulator_layout.addWidget(QLabel("💻 Modo Emulador - Sin configuración adicional"))
        emulator_layout.addStretch()
        
        # Widget para WiFi
        wifi_widget = QWidget()
        wifi_layout = QHBoxLayout(wifi_widget)
        wifi_layout.addWidget(QLabel("📡 IP ELM327:"))
        
        self.wifi_ip_input = QLineEdit("192.168.0.10")
        self.wifi_ip_input.setPlaceholderText("Ej: 192.168.0.10")
        wifi_layout.addWidget(self.wifi_ip_input)
        
        wifi_layout.addWidget(QLabel("Puerto:"))
        self.wifi_port_input = QLineEdit("35000")
        self.wifi_port_input.setPlaceholderText("35000")
        self.wifi_port_input.setMaximumWidth(80)
        wifi_layout.addWidget(self.wifi_port_input)
        
        # Botón test WiFi
        self.test_wifi_btn = QPushButton("🔍 Test WiFi")
        self.test_wifi_btn.clicked.connect(self.test_wifi_connection)
        wifi_layout.addWidget(self.test_wifi_btn)
        
        wifi_layout.addStretch()
        
        # Widget para USB
        usb_widget = QWidget()
        usb_layout = QHBoxLayout(usb_widget)
        usb_layout.addWidget(QLabel("🔌 Puerto COM:"))
        
        self.port_combo = QComboBox()
        self.port_combo.addItems(["COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8"])
        usb_layout.addWidget(self.port_combo)
        
        # Botón escanear puertos
        self.scan_ports_btn = QPushButton("🔍 Escanear")
        self.scan_ports_btn.clicked.connect(self.scan_com_ports)
        usb_layout.addWidget(self.scan_ports_btn)
        
        usb_layout.addStretch()
        
        # Agregar widgets al stack
        self.config_stack.addWidget(emulator_widget)
        self.config_stack.addWidget(wifi_widget)
        self.config_stack.addWidget(usb_widget)
        
        layout.addWidget(self.config_stack)
        
        # Fila 3: Botones de control
        buttons_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("🔌 Conectar")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("font-weight: bold; padding: 8px; font-size: 12px;")
        
        self.start_btn = QPushButton("▶️ Iniciar Lectura")
        self.start_btn.clicked.connect(self.start_reading)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("font-weight: bold; padding: 8px; font-size: 12px;")
        
        self.stop_btn = QPushButton("⏹️ Detener")
        self.stop_btn.clicked.connect(self.stop_reading)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("font-weight: bold; padding: 8px; font-size: 12px;")
        
        buttons_layout.addWidget(self.connect_btn)
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        return group_box
        
    def create_data_panel(self):
        """Crear panel de visualización de datos"""
        group_box = QGroupBox("📊 Datos OBD-II en Tiempo Real")
        layout = QGridLayout(group_box)
        
        self.data_labels = {}
        pids = [
            ('RPM', 'rpm'),
            ('Velocidad (km/h)', 'vel'), 
            ('Temperatura (°C)', 'temp'),
            ('MAF (g/s)', 'maf'),
            ('Throttle (%)', 'throttle'),
            ('Voltaje Batería (V)', 'volt_bateria')
        ]
        
        for i, (display_name, pid) in enumerate(pids):
            label = QLabel(f"{display_name}:")
            label.setStyleSheet("font-weight: bold; font-size: 12px;")
            
            value_label = QLabel("--")
            value_label.setStyleSheet("""
                font-weight: bold; 
                font-size: 18px; 
                color: #2E8B57;
                border: 2px solid #ccc;
                padding: 8px;
                background-color: #f0f0f0;
                min-width: 120px;
                border-radius: 5px;
            """)
            
            row = i // 2
            col = (i % 2) * 2
            
            layout.addWidget(label, row, col)
            layout.addWidget(value_label, row, col + 1)
            
            self.data_labels[pid] = value_label
            
        return group_box
        
    def on_mode_changed(self, mode):
        """Cambiar configuración según el modo seleccionado"""
        mode_map = {
            "Emulador": 0,
            "WiFi ELM327": 1, 
            "USB/Serial": 2
        }
        
        self.config_stack.setCurrentIndex(mode_map.get(mode, 0))
        self.status_bar.showMessage(f"Modo {mode} seleccionado - Configure y conecte")
        
    def test_wifi_connection(self):
        """Probar conexión WiFi básica"""
        ip = self.wifi_ip_input.text()
        port = int(self.wifi_port_input.text())
        
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                QMessageBox.information(self, "Test WiFi", 
                    f"✅ Conexión exitosa a {ip}:{port}")
            else:
                QMessageBox.warning(self, "Test WiFi", 
                    f"❌ No se puede conectar a {ip}:{port}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Test WiFi", f"Error: {e}")
    
    def scan_com_ports(self):
        """Escanear puertos COM disponibles"""
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            
            self.port_combo.clear()
            for port in ports:
                self.port_combo.addItem(f"{port.device} - {port.description}")
                
            if ports:
                QMessageBox.information(self, "Escaneo COM", 
                    f"✅ Encontrados {len(ports)} puertos")
            else:
                QMessageBox.warning(self, "Escaneo COM", 
                    "❌ No se encontraron puertos COM")
                    
        except Exception as e:
            QMessageBox.critical(self, "Escaneo COM", f"Error: {e}")
        
    def toggle_connection(self):
        """Alternar conexión según el modo seleccionado"""
        if not self.data_source.get_connection_status():
            # Conectar
            mode = self.mode_combo.currentText()
            
            if mode == "Emulador":
                self.data_source.set_connection_mode("emulator")
                
            elif mode == "WiFi ELM327":
                ip = self.wifi_ip_input.text()
                port = int(self.wifi_port_input.text())
                self.data_source.set_connection_mode("wifi", ip=ip, port=port)
                
            elif mode == "USB/Serial":
                port = self.port_combo.currentText().split(" - ")[0]
                self.data_source.set_connection_mode("usb", port=port)
            
            if self.data_source.connect():
                self.connect_btn.setText("🔌 Desconectar")
                self.start_btn.setEnabled(True)
                # Configurar PIDs por defecto
                default_pids = ['rpm', 'vel', 'temp', 'maf', 'throttle', 'volt_bateria']
                self.data_source.set_selected_pids(default_pids)
                print(f"✅ Conexión establecida en modo {mode}")
        else:
            # Desconectar
            self.stop_reading()
            self.data_source.disconnect()
            self.connect_btn.setText("🔌 Conectar")
            self.start_btn.setEnabled(False)
            # Limpiar datos
            for label in self.data_labels.values():
                label.setText("--")
            print("🔌 Conexión terminada")
            
    def start_reading(self):
        """Iniciar lectura de datos"""
        self.data_timer.start(1000)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        print("▶️ Lectura de datos iniciada")
        
    def stop_reading(self):
        """Detener lectura de datos"""
        self.data_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        print("⏹️ Lectura de datos detenida")
        
    def read_data(self):
        """Leer datos del OBD"""
        self.data_source.read_data()
        
    def update_display(self, data):
        """Actualizar visualización con nuevos datos"""
        for pid, value in data.items():
            if pid in self.data_labels:
                if pid == 'rpm':
                    formatted_value = f"{value:,} RPM"
                elif pid == 'vel':
                    formatted_value = f"{value} km/h"
                elif pid == 'temp':
                    formatted_value = f"{value}°C"
                elif pid == 'maf':
                    formatted_value = f"{value} g/s"
                elif pid == 'throttle':
                    formatted_value = f"{value}%"
                elif pid == 'volt_bateria':
                    formatted_value = f"{value}V"
                else:
                    formatted_value = str(value)
                    
                self.data_labels[pid].setText(formatted_value)
                
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_bar.showMessage(f"Última actualización: {timestamp}")
                    
    def update_status(self, status):
        """Actualizar barra de estado"""
        self.status_bar.showMessage(status)

def main():
    """Función principal"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    try:
        setup_logging()
    except:
        logging.basicConfig(level=logging.INFO)
    
    print("🚀 Iniciando Dashboard OBD-II WiFi/USB...")
    print("✅ Sistema con soporte completo WiFi ELM327")
    
    dashboard = OBDDashboard()
    dashboard.show()
    
    print("📊 Dashboard listo - Ventana abierta")
    print("💡 Instrucciones:")
    print("   WIFI: Selecciona 'WiFi ELM327' → Configura IP → Conectar")
    print("   USB: Selecciona 'USB/Serial' → Elige puerto → Conectar")
    print("   TEST: Selecciona 'Emulador' → Conectar → Iniciar Lectura")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
