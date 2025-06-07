from typing import Dict, Optional, Any, Mapping, cast, TypeVar, Union
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QGroupBox, QComboBox, QLineEdit, QStatusBar
)
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

if os.path.exists('src'):
    sys.path.append('src')

try:
    from src.obd.connection_base import OBD2Connection
    from src.obd.connection_wifi import OBD2WiFiConnection
    from src.obd.elm327_improved import ELM327
    from src.obd.pid_parser import PIDParser
    from src.obd.emulador import EmuladorOBD
    from src.utils.logging_app import setup_logging
except ImportError as e:
    print(f"Error importando módulos OBD: {e}")
    print("Implementando versiones básicas...")
    
    class OBD2Connection:
        def connect(self) -> bool: return False
        def disconnect(self) -> bool: return True
        
    class OBD2WiFiConnection(OBD2Connection): pass
    class ELM327:
        def __init__(self, conn: OBD2Connection, parser: Any): pass
        def initialize(self) -> bool: return False
        def cleanup(self) -> None: pass
        def read_pids(self, pids: list) -> Dict[str, float]: return {}
        
    class PIDParser:
        def load_standard_pids(self, path: str) -> None: pass
        def load_proprietary_profile(self, name: str, path: str) -> None: pass
        
    class EmuladorOBD:
        def get_simulated_data(self, pids: list) -> Dict[str, float]: return {}
        def cleanup(self) -> None: pass
        
    def setup_logging() -> None: pass


# Tipo para valores de datos OBD
OBDValue = Union[float, None]
DataDict = Dict[str, OBDValue]

class OBDError(Exception):
    """Excepción base para errores de OBD."""
    pass


class ConnectionCleanupError(OBDError):
    """Error durante la limpieza de conexión."""
    pass


class ConnectionError(OBDError):
    """Error de conexión OBD."""
    pass


class DataError(OBDError):
    """Error en la lectura o procesamiento de datos."""
    pass


# Configuración de estilos
BUTTON_STYLE = (
    "font-weight: bold; "
    "padding: 10px; "
    "font-size: 12px"
)
VALUE_STYLE = (
    "font-weight: bold; "
    "font-size: 18px; "
    "color: #2E8B57; "
    "border: 2px solid #ccc; "
    "padding: 10px; "
    "background-color: #f0f0f0; "
    "min-width: 120px; "
    "border-radius: 5px"
)
WARNING_STYLE = (
    "font-weight: bold; "
    "font-size: 18px; "
    "color: #FF4136; "
    "border: 2px solid #FF4136; "
    "padding: 10px; "
    "background-color: #FFE5E5; "
    "min-width: 120px; "
    "border-radius: 5px"
)
CAUTION_STYLE = (
    "font-weight: bold; "
    "font-size: 18px; "
    "color: #FF851B; "
    "border: 2px solid #FF851B; "
    "padding: 10px; "
    "background-color: #FFF3E5; "
    "min-width: 120px; "
    "border-radius: 5px"
)
MODE_LABEL_STYLE = (
    "font-weight: bold; "
    "font-size: 14px; "
    "color: {color}; "
    "padding: 10px; "
    "background-color: {bg_color}; "
    "border: 2px solid {border_color}; "
    "border-radius: 5px"
)


class OBDDataSource(QObject):
    """Fuente de datos OBD-II con soporte para modos real y emulado."""

    data_received = pyqtSignal(Dict[str, Union[float, None]])
    status_changed = pyqtSignal(str)
    mode_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Componentes principales
        self._connection: Optional[OBD2Connection] = None
        self._elm: Optional[ELM327] = None
        self._parser = PIDParser()
        self._emulator: Optional[EmuladorOBD] = None
        
        # Estado
        self.connection_mode = "emulator"
        self.is_connected = False
        self.selected_pids: list[str] = []
        self.supported_pids: set[str] = set()
        
        # Configuración
        self.usb_port = "COM3"
        self.wifi_ip = "192.168.0.10"
        self.wifi_port = 35000
        
        # Cargar configuración
        self._load_configuration()

    def cleanup(self) -> bool:
        """Limpia recursos y desconecta."""
        try:
            self._cleanup_current_connection()
            self.is_connected = False
            self.status_changed.emit("🔌 Desconectado")
            self.logger.info("Desconectado de todos los modos")
            return True
        except Exception as e:
            self.logger.error(f"Error desconectando: {e}")
            return False

    def force_disconnect(self) -> bool:
        """Fuerza la desconexión y limpieza de recursos."""
        return self.cleanup()

    def _cleanup_current_connection(self) -> None:
        """Limpia la conexión actual de forma segura y libera recursos."""
        try:
            if self._elm:
                self.logger.debug("Limpiando conexión ELM327...")
                try:
                    if hasattr(self._elm, 'cleanup'):
                        self._elm.cleanup()
                except Exception as e:
                    self.logger.warning(f"Error limpiando ELM327: {e}")
                finally:
                    self._elm = None

            if self._connection:
                self.logger.debug("Cerrando conexión OBD...")
                try:
                    self._connection.disconnect()
                except Exception as e:
                    self.logger.warning(f"Error cerrando conexión: {e}")
                finally:
                    self._connection = None

            if self._emulator:
                self.logger.debug("Deteniendo emulador...")
                try:
                    if hasattr(self._emulator, 'cleanup'):
                        self._emulator.cleanup()
                except Exception as e:
                    self.logger.warning(f"Error deteniendo emulador: {e}")
                finally:
                    self._emulator = None

            # Restablecer estado
            self.supported_pids.clear()
            self.selected_pids.clear()
            self.is_connected = False
            
            self.logger.info("Limpieza de conexión completada")
            
        except Exception as e:
            self.logger.error(f"Error durante la limpieza: {e}")
            raise ConnectionCleanupError(str(e)) from e

    def _load_configuration(self) -> None:
        """Carga configuración de PIDs y perfiles."""
        try:
            # Cargar PIDs estándar
            config_dir = Path(__file__).parent / "config"
            pids_file = config_dir / "pids_standard.csv"
            self._parser.load_standard_pids(str(pids_file))
            
            # Cargar perfiles propietarios
            profiles_dir = config_dir / "profiles"
            if profiles_dir.exists():
                for profile in profiles_dir.glob("*.json"):
                    self._parser.load_proprietary_profile(
                        profile.stem,
                        str(profile)
                    )
            
            self.logger.info("Configuración cargada correctamente")
            
        except Exception as e:
            self.logger.error(f"Error cargando configuración: {e}")
            
    def set_selected_pids(self, pids: list[str]) -> None:
        """Configura PIDs a monitorear."""
        if self.connection_mode != "emulator":
            # En modo real, filtrar solo PIDs soportados
            pids = [pid for pid in pids if pid in self.supported_pids]
            
        self.selected_pids = pids[:8]  # Limitar a 8 PIDs
        self.logger.info(f"PIDs configurados: {self.selected_pids}")

    def read_data(self) -> DataDict:
        """Lee datos según modo actual."""
        if not self.is_connected:
            return {}
            
        try:
            if self.connection_mode == "emulator":
                return self._read_emulator_data()
            else:
                return self._read_real_data()
                
        except Exception as e:
            self.logger.error(f"Error leyendo datos: {e}")
            return {}
            
    def _read_emulator_data(self) -> DataDict:
        """Lee datos del emulador."""
        if not self._emulator:
            return {}
            
        data = self._emulator.get_simulated_data(self.selected_pids)
        if data:
            # Convertir todos los valores a float o None
            clean_data: DataDict = {
                k: float(v) if v is not None else None 
                for k, v in data.items()
            }
            self.data_received.emit(clean_data)
            return clean_data
        return {}
        
    def _read_real_data(self) -> DataDict:
        """Lee datos del vehículo real."""
        if not self._elm:
            return {}
            
        try:
            data = self._elm.read_pids(self.selected_pids)
            if data:
                # Convertir todos los valores a float o None
                clean_data: DataDict = {
                    k: float(v) if v is not None else None 
                    for k, v in data.items()
                }
                self.data_received.emit(clean_data)
                return clean_data
            return {}
        except Exception as e:
            self.logger.error(f"Error leyendo datos reales: {e}")
            return {}
        
    def connect(self) -> bool:
        """Establece conexión según modo actual."""
        self.logger.info(f"Iniciando conexión en modo: {self.connection_mode}")
        
        try:
            # Limpiar cualquier conexión previa
            self._cleanup_current_connection()
            
            if self.connection_mode == "emulator":
                self._emulator = EmuladorOBD()
                self.is_connected = True
                self.status_changed.emit("✅ Conectado (EMULADOR)")
                return True
                
            elif self.connection_mode == "wifi":
                # Crear conexión WiFi con los parámetros disponibles
                self._connection = OBD2WiFiConnection(self.wifi_ip, self.wifi_port)
                
                if self._connection.connect():
                    # Inicializar ELM327
                    self._elm = ELM327(self._connection, self._parser)
                    if self._elm.initialize():
                        self.is_connected = True
                        
                        # Obtener PIDs soportados si están disponibles
                        if hasattr(self._elm, 'get_supported_pids'):
                            supported = self._elm.get_supported_pids()
                            self.supported_pids = set(supported)
                        
                        # Formatear mensaje de estado
                        host = self.wifi_ip
                        port = self.wifi_port
                        msg = f"✅ WiFi: {host}:{port}"
                        self.status_changed.emit(msg)
                        return True
                        
                self.status_changed.emit("❌ Falló conexión OBD WiFi")
                return False
                
            else:
                msg = f"⚠️ {self.connection_mode}: no implementado"
                self.status_changed.emit(msg)
                return False
                
        except Exception as e:
            self.logger.exception("Error en conexión")
            self.status_changed.emit(f"💥 ERROR: {e}")
            return False
