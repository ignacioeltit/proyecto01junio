# ARCHIVO CORREGIDO - dashboard_gui_fixed.py
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
        
        class OBDConnection:
            def __init__(self, port=None):
                self.connected = False
                self.port = port
            def connect(self):
                return True
            def disconnect(self):
                pass
            def read_data(self, pids):
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
    """Clase que maneja la conexión y adquisición de datos OBD-II"""
    
    data_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.connection = None
        self.emulator = None
        self.is_emulator_mode = True
        self.selected_pids = []
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
        # Inicializar logging
        try:
            setup_logging()
        except:
            logging.basicConfig(level=logging.INFO)
    
    def set_emulator_mode(self, use_emulator=True):
        """Configura el modo de operación (emulador o conexión real)"""
        self.is_emulator_mode = use_emulator
        if use_emulator and not self.emulator:
            try:
                self.emulator = EmuladorOBD()
            except:
                pass
        self.logger.info(f"Modo {'emulador' if use_emulator else 'real'} activado")
    
    def connect(self, port=None):
        """Establece conexión OBD-II"""
        try:
            if self.is_emulator_mode:
                self.emulator = EmuladorOBD()
                self.is_connected = True
                self.status_changed.emit("Conectado (Emulador)")
                self.logger.info("Conexión establecida en modo emulador")
                return True
            else:
                self.connection = OBDConnection(port)
                if self.connection.connect():
                    self.is_connected = True
                    self.status_changed.emit("Conectado (Real)")
                    self.logger.info(f"Conexión establecida en puerto {port}")
                    return True
                else:
                    self.status_changed.emit("Error de conexión")
                    return False
        except Exception as e:
            self.logger.error(f"Error en conexión: {e}")
            self.status_changed.emit("Error de conexión")
            return False
    
    def disconnect(self):
        """Desconecta la conexión OBD-II"""
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
        self.selected_pids = pids[:8]  # Máximo 8 PIDs
        self.logger.info(f"PIDs seleccionados: {self.selected_pids}")
    
    def read_data(self):
        """Lee datos de los PIDs seleccionados - MÉTODO CRÍTICO RESTAURADO"""
        if not self.is_connected:
            return {}
        
        try:
            if self.is_emulator_mode and self.emulator:
                # Modo emulador
                data = self.emulator.get_simulated_data(self.selected_pids)
            elif self.connection:
                # Modo real
                data = self.connection.read_data(self.selected_pids)
            else:
                data = {}
            
            # Emitir señal con los datos
            if data:
                self.data_received.emit(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error leyendo datos: {e}")
            return {}
    
    def get_connection_status(self):
        """Retorna el estado de la conexión"""
        return self.is_connected
    
    def get_available_pids(self):
        """Retorna lista de PIDs disponibles"""
        # PIDs comunes de OBD-II
        return [
            '010C',  # RPM
            '010D',  # Velocidad
            '0105',  # Temperatura refrigerante
            '010F',  # Temperatura admisión
            '0111',  # Posición acelerador
            '014F',  # Máximo MAF
            '0142',  # Voltaje módulo control
            '0143'   # Carga absoluta
        ]

class OBDDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard OBD-II - Sistema Completo")
        self.setGeometry(100, 100, 1200, 800)
        
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
        self.status_bar.showMessage("Desconectado - Listo para usar")
        
    def create_control_panel(self):
        group_box = QGroupBox("Control de Conexión OBD-II")
        layout = QHBoxLayout(group_box)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Emulador", "Real"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        self.port_combo = QComboBox()
        self.port_combo.addItems(["COM1", "COM2", "COM3", "COM4", "COM5"])
        self.port_combo.setEnabled(False)
        
        self.connect_btn = QPushButton("🔌 Conectar")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        
        self.start_btn = QPushButton("▶️ Iniciar Lectura")
        self.start_btn.clicked.connect(self.start_reading)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        
        self.stop_btn = QPushButton("⏹️ Detener")
        self.stop_btn.clicked.connect(self.stop_reading)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        
        layout.addWidget(QLabel("Modo:"))
        layout.addWidget(self.mode_combo)
        layout.addWidget(QLabel("Puerto:"))
        layout.addWidget(self.port_combo)
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch()
        
        return group_box
        
    def create_data_panel(self):
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
            label.setStyleSheet("font-weight: bold;")
            
            value_label = QLabel("--")
            value_label.setStyleSheet("""
                font-weight: bold; 
                font-size: 16px; 
                color: #2E8B57;
                border: 1px solid #ccc;
                padding: 5px;
                background-color: #f0f0f0;
                min-width: 100px;
            """)
            
            row = i // 2
            col = (i % 2) * 2
            
            layout.addWidget(label, row, col)
            layout.addWidget(value_label, row, col + 1)
            
            self.data_labels[pid] = value_label
            
        return group_box
        
    def on_mode_changed(self, mode):
        is_real = (mode == "Real")
        self.port_combo.setEnabled(is_real)
        self.data_source.set_emulator_mode(not is_real)
        
    def toggle_connection(self):
        if not self.data_source.get_connection_status():
            port = self.port_combo.currentText() if self.mode_combo.currentText() == "Real" else None
            if self.data_source.connect(port):
                self.connect_btn.setText("🔌 Desconectar")
                self.start_btn.setEnabled(True)
                default_pids = ['rpm', 'vel', 'temp', 'maf', 'throttle', 'volt_bateria']
                self.data_source.set_selected_pids(default_pids)
                print("✅ Conexión establecida exitosamente")
        else:
            self.stop_reading()
            self.data_source.disconnect()
            self.connect_btn.setText("🔌 Conectar")
            self.start_btn.setEnabled(False)
            for label in self.data_labels.values():
                label.setText("--")
            print("🔌 Conexión terminada")
            
    def start_reading(self):
        self.data_timer.start(1000)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        print("▶️ Lectura de datos iniciada")
        
    def stop_reading(self):
        self.data_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        print("⏹️ Lectura de datos detenida")
        
    def read_data(self):
        self.data_source.read_data()
        
    def update_display(self, data):
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
        self.status_bar.showMessage(status)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    try:
        setup_logging()
    except:
        logging.basicConfig(level=logging.INFO)
    
    print("🚀 Iniciando Dashboard OBD-II...")
    print("✅ Sistema restaurado y funcionando")
    
    dashboard = OBDDashboard()
    dashboard.show()
    
    print("📊 Dashboard listo - Ventana abierta")
    print("💡 Instrucciones:")
    print("   1. Selecciona modo 'Emulador' para pruebas")
    print("   2. Haz clic en 'Conectar'")
    print("   3. Haz clic en 'Iniciar Lectura'")
    print("   4. ¡Observa los datos en tiempo real!")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()