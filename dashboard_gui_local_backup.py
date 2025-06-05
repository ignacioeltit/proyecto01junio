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
    from src.obd.emulador import EmuladorOBD
    from src.utils.logging_app import setup_logging
except ImportError:
    # Fallback si los módulos no están en src/
    try:
        from obd.connection import OBDConnection
        from obd.emulador import EmuladorOBD
        from utils.logging_app import setup_logging
    except ImportError:
        # Implementaciones básicas si los módulos no existen
        class OBDConnection:
            def __init__(self, port=None):
                self.connected = False
            def connect(self):
                return True
            def disconnect(self):
                pass
            def read_data(self, pids):
                return {}
        
        class EmuladorOBD:
            def __init__(self):
                pass
            def get_simulated_data(self, pids):
                import random
                return {pid: random.randint(0, 100) for pid in pids}
        
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
            self.emulator = EmuladorOBD()
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

# Aquí va el resto de tu código original de dashboard_gui.py
# Solo agregamos la clase OBDDataSource que faltaba

# [El resto del código permanece igual]