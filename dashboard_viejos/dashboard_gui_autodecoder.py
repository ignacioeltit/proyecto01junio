import json
import logging
import os
import socket
import sys
import time
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (QApplication, QComboBox, QGroupBox, QLabel,
                             QMainWindow, QMessageBox, QVBoxLayout, QWidget)

# Agregar el directorio src al path si existe
if os.path.exists('src'):
    sys.path.append('src')

try:
    # Importaciones básicas OBD
    from src.obd.connection import OBDConnection
    from src.obd.emulador import EmuladorOBD
    from src.obd.test_hilux_emulator import HiluxDieselEmulador  # Nuevo emulador Hilux
    from src.obd.pid_decoder import PIDDecoder, get_supported_pids
    from src.obd.elm327 import ELM327  # Importar ELM327
    # Importaciones para autodetección y decodificador universal
    from src.obd.protocol_detector import ProtocolDetector
    from src.utils.logging_app import setup_logging
except ImportError as e:
    print(f"🔧 Usando implementaciones básicas... Error: {e}")
    from obd_connection import OBDConnection
    from obd_emulador import EmuladorOBD
    from utils.logging_app import setup_logging

# Configuración del logger
def setup_enhanced_logging():
    """Configura sistema de logging mejorado con rotación de archivos"""
    import logging
    from logging.handlers import RotatingFileHandler
    import os
    from datetime import datetime
    
    # Crear directorio de logs si no existe
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Nombre del archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"dashboard_{timestamp}.log")
    
    # Configurar handler con rotación
    handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5
    )
    
    # Formato detallado
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)
    
    # Logger específico para la aplicación
    app_logger = logging.getLogger('dashboard')
    app_logger.setLevel(logging.DEBUG)
    
    # Handler para consola con menos detalle
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        '%(levelname)s: %(message)s'
    ))
    app_logger.addHandler(console)
    
    return app_logger


# Configurar logging al inicio
logger = setup_enhanced_logging()

def log_exception(e: Exception, context: str = ""):
    """Función helper para logging de excepciones"""
    import traceback
    
    logger.error(
        f"Error en {context}: {str(e)}\n" +
        "".join(traceback.format_tb(e.__traceback__))
    )

class DashboardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Configuración de la ventana principal
        self.setWindowTitle("Dashboard OBD-II")
        self.setGeometry(100, 100, 800, 600)

        # Sistema de diagnóstico
        self.diagnostic = DiagnosticManager()
        self.perf_monitor = PerformanceMonitor()
        
        # Cache y recursos
        self._cache = {}
        self._max_cache_size = 1000
        self._last_cleanup = time.time()
        self._cleanup_interval = 60
        self._check_interval = 5
        self._last_check = time.time()

        # Inicializar conexión OBD
        self.obd_connection = None
        self.init_obd_connection()

        # Estado de la aplicación
        self._is_running = False
        self._error_count = 0
        self._diagnostic_interval = 30

        # Configurar UI y timer de diagnóstico
        self.init_ui()
        self._setup_diagnostic_timer()
        
    def _setup_diagnostic_timer(self):
        """Configura timer para chequeos periódicos"""
        from PyQt6.QtCore import QTimer
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._periodic_check)
        self._check_timer.start(1000)  # Check cada segundo
        
    def _periodic_check(self):
        """Realiza chequeos periódicos de salud del sistema"""
        current_time = time.time()
        
        if current_time - self._last_check < self._check_interval:
            return
            
        try:
            # Verificar salud del sistema
            if not self.diagnostic.check_system_health():
                self._handle_health_warning()
                
            # Verificar rendimiento
            if not self.perf_monitor.check_performance():
                self._handle_performance_warning()
                
            # Realizar limpieza si es necesario
            if current_time - self._last_cleanup > self._cleanup_interval:
                self.cleanup_resources()
                
            self._last_check = current_time
            
        except Exception as e:
            logger.error(f"Error en chequeo periódico: {e}")
            
    def _handle_health_warning(self):
        """Maneja advertencias de salud del sistema"""
        report = self.diagnostic.get_health_report()
        
        msg = ["⚠️ Advertencias del sistema:"]
        
        if report.get('memory_mb', 0) > 500:
            msg.append(f"- Memoria: {report['memory_mb']:.1f}MB")
            
        if report.get('cpu_percent', 0) > 70:
            msg.append(f"- CPU: {report['cpu_percent']:.1f}%")
            
        if report.get('conn_errors', 0) > 0:
            msg.append(f"- Errores conexión: {report['conn_errors']}")
            
        if len(msg) > 1:  # Si hay advertencias
            QMessageBox.warning(
                self, 
                "Estado del Sistema",
                "\n".join(msg)
            )
            
    def _handle_performance_warning(self):
        """Maneja advertencias de rendimiento"""
        stats = self.perf_monitor.get_stats()
        
        if not stats:
            return
            
        msg = ["⚠️ Advertencias de rendimiento:"]
        
        if stats['avg_read_time'] > 0.5:
            msg.append(f"- Lecturas lentas: {stats['avg_read_time']:.2f}s")
            
        if stats['avg_decode_time'] > 0.1:
            msg.append(f"- Decodificación lenta: {stats['avg_decode_time']:.2f}s")
            
        if len(msg) > 1:
            QMessageBox.warning(
                self,
                "Rendimiento",
                "\n".join(msg)
            )

    def init_obd_connection(self):
        # Intentar conexión OBD
        try:
            self.obd_connection = OBDConnection()
            self.obd_connection.connect()
            logger.info("Conexión OBD establecida.")
        except Exception as e:
            logger.error(f"Error al conectar OBD: {e}")
            QMessageBox.critical(self, "Error de conexión", f"No se pudo conectar al dispositivo OBD-II: {e}")

    def init_ui(self):
        # Configuración de la interfaz de usuario
        # ...widgets y layout...
        self.show()

    def cleanup_resources(self):
        """Limpia recursos y caché si han pasado _cleanup_interval segundos"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            # Limpiar caché si excede el tamaño máximo
            if len(self._cache) > self._max_cache_size:
                # Mantener solo las últimas _max_cache_size/2 entradas
                items = sorted(self._cache.items(), key=lambda x: x[1]['timestamp'])
                self._cache = dict(items[-self._max_cache_size//2:])
            
            # Forzar recolección de basura
            import gc
            gc.collect()
            
            self._last_cleanup = current_time
            logger.debug("Limpieza de recursos completada")

    def run_diagnostic(self):
        """Ejecuta diagnóstico completo del sistema"""
        if time.time() - self._last_diagnostic < self._diagnostic_interval:
            return
            
        try:
            # Verificar rendimiento
            if not self.perf_monitor.check_performance():
                self.show_performance_warning()
                
            # Verificar recursos
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            
            if mem_info.rss > 500 * 1024 * 1024:  # 500MB
                self.cleanup_resources()
                logger.warning("Alto uso de memoria - limpieza ejecutada")
                
            # Verificar estado de conexión
            if self.obd_connection and not self._verify_connection():
                self._handle_connection_error()
                
            self._last_diagnostic = time.time()
            
        except Exception as e:
            logger.error(f"Error en diagnóstico: {e}")
            
    def _verify_connection(self):
        """Verifica estado de conexión OBD"""
        if not self.obd_connection:
            return False
            
        try:
            # Intenta leer un PID básico para verificar conexión
            result = self.obd_connection.read_data(['0100'])
            return bool(result)
        except Exception:
            return False
            
    def _handle_connection_error(self):
        """Maneja errores de conexión"""
        self._error_count += 1
        
        if self._error_count >= 3:
            self.reconnect_obd()
            self._error_count = 0
            
    def reconnect_obd(self):
        """Intenta reconexión OBD"""
        logger.info("Intentando reconexión OBD...")
        
        if self.obd_connection:
            try:
                self.obd_connection.disconnect()
            except Exception:
                pass
                
        time.sleep(2)  # Espera para estabilización
        self.init_obd_connection()
        
    def show_performance_warning(self):
        """Muestra advertencia de rendimiento"""
        stats = self.perf_monitor.get_stats()
        if not stats:
            return
            
        msg = ("Advertencia de rendimiento:\n" +
               f"- Tiempo medio de lectura: {stats['avg_read_time']:.2f}s\n" +
               f"- Tiempo medio decode: {stats['avg_decode_time']:.2f}s\n" +
               f"- Tasa de errores: {stats['error_rate']:.2f}/s")
               
        QMessageBox.warning(self, "Rendimiento", msg)

    def closeEvent(self, event: QCloseEvent):
        """Manejo de cierre de aplicación"""
        self._is_running = False
        
        # Limpiar recursos
        if self.obd_connection:
            try:
                self.obd_connection.disconnect()
                logger.info("Conexión OBD cerrada")
            except Exception as e:
                logger.error(f"Error al cerrar conexión OBD: {e}")
        
        # Limpiar caché y liberar memoria
        self._cache.clear()
        import gc
        gc.collect()
        
        event.accept()

class OBDDataSource(QObject):
    """Fuente de datos OBD-II con optimización de memoria y recursos"""
    
    # Señales
    data_received = pyqtSignal(dict)
    status_changed = pyqtSignal(str)
    mode_changed = pyqtSignal(str)
    
    # Constantes
    MAX_CACHE_SIZE = 1000
    CLEANUP_INTERVAL = 60  # segundos
    
    def __init__(self):
        super().__init__()
        # Estado de conexión
        self.connection = None
        self.emulator = None
        self.connection_mode = "emulator"
        self.is_connected = False
        
        # Configuración
        self.logger = logging.getLogger(__name__)
        self.usb_port = "COM3"
        self.wifi_ip = "192.168.0.10" 
        self.wifi_port = 35000
        
        # Decodificación y PIDs
        self.pid_decoder = PIDDecoder()
        self.supported_pids = []
        self.selected_pids = []
        self.profile_path = None
        
        # Cache y optimización
        self._data_cache = {}
        self._last_cleanup = time.time()
        self._failed_reads = 0
        self._max_failed_reads = 3
        
        # Monitor de rendimiento
        self.performance_monitor = PerformanceMonitor()

    def connect(self):
        print(f"🔌 CONECTANDO EN MODO: {self.connection_mode}")
        try:
            if self.connection_mode == "emulator":
                print("🤖 Inicializando EMULADOR HILUX...")
                self.emulator = HiluxDieselEmulador()  # Usar el nuevo emulador
                self.is_connected = True
                self.status_changed.emit("✅ Conectado (EMULADOR HILUX)")
                return True
            elif self.connection_mode == "wifi":
                print(f"📡 Inicializando WIFI {self.wifi_ip}:{self.wifi_port}...")
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(3)
                test_result = test_sock.connect_ex((self.wifi_ip, self.wifi_port))
                test_sock.close()
                if test_result != 0:
                    error_msg = f"❌ No hay conectividad TCP a {self.wifi_ip}:{self.wifi_port}"
                    print(error_msg)
                    self.status_changed.emit(error_msg)
                    return False
                self.connection = OBDConnection(
                    mode="wifi",
                    ip=self.wifi_ip,
                    tcp_port=self.wifi_port,
                    timeout=5
                )
                if self.connection.connect():
                    self.is_connected = True
                    success_msg = f"✅ Conectado (WIFI {self.wifi_ip}:{self.wifi_port})"
                    print(success_msg)
                    self.status_changed.emit(success_msg)
                    # Autodetectar protocolo y escanear PIDs
                    if not self.autodetect_protocol_and_scan_pids():
                        return False
                    return True
                else:
                    error_msg = "❌ Falló conexión OBD WiFi"
                    print(error_msg)
                    self.status_changed.emit(error_msg)
                    return False
            elif self.connection_mode == "usb":
                print(f"🔌 Inicializando USB {self.usb_port}...")
                self.status_changed.emit("⚠️ USB no implementado aún")
                return False
        except Exception as e:
            error_msg = f"💥 ERROR: {e}"
            print(error_msg)
            self.status_changed.emit(error_msg)
            return False

    def _scan_pid_group(self, cmd):
        """Escanea un grupo de PIDs y retorna los soportados"""
        try:
            resp = self.elm327.send_pid(cmd)
            if not resp or "NO DATA" in resp.upper():
                return []
                
            hex_mask = resp.replace(" ", "")
            if not (hex_mask.startswith("41" + cmd[2:]) and len(hex_mask) >= 8):
                return []
                
            mask = int(hex_mask[4:12], 16)
            base_pid = int(cmd[2:], 16)
            pids = []
            
            for i in range(32):
                if mask & (1 << (31 - i)):
                    pid = f"01{base_pid + i + 1:02X}"
                    pids.append(pid)
                    
            return pids
        except Exception as e:
            print(f"Error escaneando grupo {cmd}: {e}")
            return []

    def autodetect_protocol_and_scan_pids(self):
        """Autodetecta el protocolo y escanea los PIDs soportados"""
        try:
            # Inicializar el ELM327
            self.elm327 = ELM327(self.connection)
            if not self.elm327.initialize():
                self.status_changed.emit("❌ Falló inicialización ELM327")
                return False
                
            # Importar y usar el nuevo manejador
            from src.obd.protocol_handler import ProtocolHandler
            handler = ProtocolHandler(self.elm327)
            self.status_changed.emit("⚙️ Escaneando PIDs soportados...")
            
            # Escanear PIDs
            self.supported_pids = handler.scan_pids()
            if not self.supported_pids:
                self.status_changed.emit("⚠️ No se detectaron PIDs soportados")
                return False

            # Seleccionar PIDs básicos comunes
            basic_pids = ["010C", "010D"]  # RPM y velocidad
            self.selected_pids = [pid for pid in basic_pids if pid in self.supported_pids]
            
            if not self.selected_pids:
                self.logger.warning("No se encontraron PIDs básicos soportados")
                # Intentar con todos los PIDs soportados hasta 5
                self.selected_pids = self.supported_pids[:5]
            
            msg = f"✅ PIDs detectados: {len(self.supported_pids)}, Seleccionados: {len(self.selected_pids)}"
            print(msg)
            self.logger.info(msg)
            self.status_changed.emit(msg)
            return True
            
        except Exception as e:
            error_msg = f"❌ Error en detección: {str(e)}"
            print(error_msg)
            self.logger.error(error_msg)
            self.status_changed.emit(error_msg)
            return False

    def cleanup_cache(self):
        """Limpia el caché si es necesario"""
        current_time = time.time()
        if current_time - self._last_cleanup > self.CLEANUP_INTERVAL:
            # Mantener solo entradas recientes
            old_size = len(self._data_cache)
            self._data_cache = {
                k: v for k, v in self._data_cache.items() 
                if current_time - v['timestamp'] < 300  # 5 minutos
            }
            new_size = len(self._data_cache)
            if old_size != new_size:
                self.logger.debug(
                    f"Cache limpiado: {old_size - new_size} entradas eliminadas"
                )
            self._last_cleanup = current_time

    def read_data(self):
        """Lee datos con manejo optimizado de memoria"""
        if not self.is_connected:
            return {}
            
        self.cleanup_cache()
        
        try:
            start_time = time.time()
            if self.connection_mode == "emulator" and self.emulator:
                data = self._read_emulator_data()
            elif self.connection_mode == "wifi" and self.connection:
                data = self._read_wifi_data()
            else:
                return {}
                
            elapsed_time = time.time() - start_time
            self.performance_monitor.log_read_time(elapsed_time)
            
            self._failed_reads = 0
            return data
            
        except Exception as e:
            self._failed_reads += 1
            if self._failed_reads >= self._max_failed_reads:
                self.status_changed.emit("⚠️ Múltiples errores de lectura")
                self.is_connected = False
            self.logger.error(f"Error leyendo datos: {e}")
            return {}
            
    def _read_emulator_data(self):
        """Lee datos del emulador con cache"""
        data = self.emulator.get_simulated_data(self.selected_pids)
        self._cache_data(data)
        self.data_received.emit(data)
        return data
        
    def _read_wifi_data(self):
        """Lee datos WiFi con decodificación optimizada"""
        raw_data = self.connection.read_data(self.selected_pids)
        data = {}
        
        # Usar caché para valores que no cambiaron
        for pid, raw in raw_data.items():
            if raw == self._get_cached_raw(pid):
                data[pid] = self._get_cached_value(pid)
                continue
                
            # Decodificar solo si el valor cambió
            start_time = time.time()
            decoded = self.pid_decoder.decode(
                pid, 
                [raw] if isinstance(raw, int) else raw
            )
            elapsed_time = time.time() - start_time
            self.performance_monitor.log_decode_time(elapsed_time)
            
            data[pid] = decoded['value']
            self._cache_data({pid: raw}, raw=True)
            self._cache_data({pid: decoded['value']})
            
        self.data_received.emit(data)
        return data
        
    def _cache_data(self, data, raw=False):
        """Almacena datos en caché con timestamp"""
        prefix = 'raw_' if raw else ''
        current_time = time.time()
        
        for pid, value in data.items():
            self._data_cache[f"{prefix}{pid}"] = {
                'value': value,
                'timestamp': current_time
            }
            
    def _get_cached_raw(self, pid):
        """Obtiene valor raw del caché"""
        cache_entry = self._data_cache.get(f"raw_{pid}")
        return cache_entry['value'] if cache_entry else None
        
    def _get_cached_value(self, pid):
        """Obtiene valor decodificado del caché"""
        cache_entry = self._data_cache.get(pid)
        return cache_entry['value'] if cache_entry else None

class PerformanceMonitor:
    """Monitor de rendimiento para detectar y prevenir problemas"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.reset_stats()
        
    def reset_stats(self):
        """Reinicia estadísticas de rendimiento"""
        self.read_times = []
        self.decode_times = []
        self.error_count = 0
        self.last_warning = 0
        self.start_time = time.time()
        
    def log_read_time(self, elapsed):
        """Registra tiempo de lectura"""
        self.read_times.append(elapsed)
        if len(self.read_times) > 100:
            self.read_times.pop(0)
            
    def log_decode_time(self, elapsed):
        """Registra tiempo de decodificación"""
        self.decode_times.append(elapsed)
        if len(self.decode_times) > 100:
            self.decode_times.pop(0)
            
    def log_error(self):
        """Registra error de operación"""
        self.error_count += 1
        
    def get_stats(self):
        """Obtiene estadísticas actuales"""
        if not self.read_times or not self.decode_times:
            return {}
            
        return {
            'avg_read_time': sum(self.read_times) / len(self.read_times),
            'avg_decode_time': sum(self.decode_times) / len(self.decode_times),
            'max_read_time': max(self.read_times),
            'max_decode_time': max(self.decode_times),
            'error_rate': self.error_count / (time.time() - self.start_time),
        }
        
    def check_performance(self):
        """Verifica métricas de rendimiento"""
        stats = self.get_stats()
        if not stats:
            return True
            
        current_time = time.time()
        if current_time - self.last_warning < 60:
            return True
            
        warnings = []
        
        if stats['avg_read_time'] > 0.5:
            warnings.append(f"Lecturas lentas: {stats['avg_read_time']:.2f}s")
            
        if stats['avg_decode_time'] > 0.1:
            warnings.append(f"Decodificación lenta: {stats['avg_decode_time']:.2f}s")
            
        if stats['error_rate'] > 0.1:
            warnings.append(f"Alta tasa de errores: {stats['error_rate']:.2f}/s")
            
        if warnings:
            self.last_warning = current_time
            self.logger.warning("Advertencias de rendimiento: " + ", ".join(warnings))
            return False
            
        return True

class DiagnosticManager:
    """Gestiona diagnósticos del sistema y monitoreo de recursos"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.reset_stats()
        
    def reset_stats(self):
        """Reinicia estadísticas de diagnóstico"""
        self._stats = {
            'mem_usage': [],
            'cpu_usage': [],
            'conn_errors': 0,
            'decode_errors': 0,
            'last_check': time.time()
        }
        
    def check_system_health(self):
        """Verifica salud general del sistema"""
        try:
            import psutil
            process = psutil.Process()
            
            # Memoria
            mem = process.memory_info()
            self._stats['mem_usage'].append(mem.rss / 1024 / 1024)  # MB
            if len(self._stats['mem_usage']) > 60:
                self._stats['mem_usage'].pop(0)
                
            # CPU
            cpu = process.cpu_percent()
            self._stats['cpu_usage'].append(cpu)
            if len(self._stats['cpu_usage']) > 60:
                self._stats['cpu_usage'].pop(0)
                
            return self._analyze_stats()
            
        except ImportError:
            self.logger.warning("psutil no disponible - diagnóstico limitado")
            return True
            
    def _analyze_stats(self):
        """Analiza estadísticas y retorna estado de salud"""
        warnings = []
        
        # Análisis de memoria
        avg_mem = sum(self._stats['mem_usage']) / len(self._stats['mem_usage'])
        if avg_mem > 500:  # Más de 500MB
            warnings.append(f"Alto uso de memoria: {avg_mem:.1f}MB")
            
        # Análisis de CPU
        avg_cpu = sum(self._stats['cpu_usage']) / len(self._stats['cpu_usage'])
        if avg_cpu > 70:  # Más del 70%
            warnings.append(f"Alto uso de CPU: {avg_cpu:.1f}%")
            
        # Análisis de errores
        error_rate = (
            self._stats['conn_errors'] + self._stats['decode_errors']
        ) / max(1, time.time() - self._stats['last_check'])
        
        if error_rate > 0.1:  # Más de 1 error cada 10 segundos
            warnings.append(f"Alta tasa de errores: {error_rate:.2f}/s")
            
        if warnings:
            self.logger.warning("Diagnóstico: " + "; ".join(warnings))
            return False
            
        return True
        
    def log_error(self, error_type):
        """Registra un error para análisis"""
        if error_type == 'connection':
            self._stats['conn_errors'] += 1
        elif error_type == 'decode':
            self._stats['decode_errors'] += 1
            
    def get_health_report(self):
        """Genera reporte de salud del sistema"""
        try:
            import psutil
            process = psutil.Process()
            
            return {
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'avg_mem_mb': (
                    sum(self._stats['mem_usage']) / 
                    len(self._stats['mem_usage'])
                ),
                'avg_cpu': (
                    sum(self._stats['cpu_usage']) / 
                    len(self._stats['cpu_usage'])
                ),
                'conn_errors': self._stats['conn_errors'],
                'decode_errors': self._stats['decode_errors'],
                'uptime_s': time.time() - self._stats['last_check']
            }
            
        except ImportError:
            return {
                'conn_errors': self._stats['conn_errors'],
                'decode_errors': self._stats['decode_errors'],
                'uptime_s': time.time() - self._stats['last_check']
            }
        
# Funciones adicionales para escaneo de PIDs y decodificador
def scan_pids(connection):
    # ...código para escanear PIDs soportados...
    pass

def universal_decoder(data):
    # ...código para decodificación universal...
    pass

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = DashboardApp()
    sys.exit(app.exec())
