"""
Clase base para conexiones OBD-II con manejo robusto de errores y timeouts adaptativos.
"""
import logging
import time
from typing import Optional, Dict, List, Tuple, Any
from abc import ABC, abstractmethod
from .utils.buffer import CircularBuffer

class OBD2ConnectionError(Exception):
    """Excepción base para errores de conexión OBD-II."""
    pass

class OBD2Connection(ABC):
    def __init__(self, timeout: float = 2.0, retry_count: int = 3,
                 adaptive_timing: bool = True):
        """
        Inicializa la conexión base OBD-II.
        
        Args:
            timeout (float): Timeout base para operaciones en segundos
            retry_count (int): Número de reintentos para comandos
            adaptive_timing (bool): Si usar timing adaptativo basado en respuestas
        """
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self.retry_count = retry_count
        self.adaptive_timing = adaptive_timing
        self.connected = False
        self.protocol = None
        self.supported_pids: Dict[str, bool] = {}
        
        # Buffer circular para datos
        self.rx_buffer = CircularBuffer(max_size=4096)
        self.last_command_time = 0
        self.min_command_interval = 0.05  # 50ms mínimo entre comandos
        
        # Métricas de timing adaptativo
        self._response_times: List[float] = []
        self._max_response_times = 50  # Mantener últimos 50 tiempos
        
    @abstractmethod
    def _connect_internal(self) -> bool:
        """Implementación específica de conexión para cada tipo."""
        pass
        
    @abstractmethod
    def _disconnect_internal(self):
        """Implementación específica de desconexión para cada tipo."""
        pass
        
    @abstractmethod
    def _write_internal(self, data: bytes) -> bool:
        """Implementación específica de escritura para cada tipo."""
        pass
        
    @abstractmethod
    def _read_internal(self, size: int) -> bytes:
        """Implementación específica de lectura para cada tipo."""
        pass
        
    def connect(self) -> bool:
        """
        Establece la conexión con manejo de errores y logging.
        
        Returns:
            bool: True si conexión exitosa, False si no
        """
        self.logger.info("Iniciando conexión OBD-II...")
        try:
            if self._connect_internal():
                self.connected = True
                self.logger.info("Conexión OBD-II establecida exitosamente")
                return True
            else:
                self.logger.error("Falló la conexión OBD-II")
                return False
        except Exception as e:
            self.logger.exception("Error estableciendo conexión OBD-II", exc_info=e)
            return False
            
    def disconnect(self):
        """Cierra la conexión de forma segura."""
        if self.connected:
            try:
                self._disconnect_internal()
            except Exception as e:
                self.logger.error(f"Error al desconectar: {e}")
            finally:
                self.connected = False
                self.rx_buffer.clear()
                
    def write(self, data: str) -> bool:
        """
        Escribe comando con control de flujo y retry.
        
        Args:
            data (str): Comando a enviar
            
        Returns:
            bool: True si exitoso, False si error
        """
        if not self.connected:
            self.logger.error("Intento de escritura sin conexión activa")
            return False
            
        # Control de flujo
        elapsed = time.time() - self.last_command_time
        if elapsed < self.min_command_interval:
            time.sleep(self.min_command_interval - elapsed)
            
        # Limpiar buffer antes de enviar
        self.rx_buffer.clear()
        
        # Agregar terminadores si no presentes
        if not data.endswith('\r'):
            data += '\r'
            
        encoded = data.encode()
        for attempt in range(self.retry_count):
            try:
                if self._write_internal(encoded):
                    self.last_command_time = time.time()
                    return True
            except Exception as e:
                self.logger.warning(f"Intento {attempt + 1} fallido: {e}")
                time.sleep(0.1 * (attempt + 1))  # Backoff exponencial
                
        self.logger.error(f"Comando falló después de {self.retry_count} intentos")
        return False
        
    def read(self, size: Optional[int] = None, timeout: Optional[float] = None) -> str:
        """
        Lee respuesta con timeout adaptativo.
        
        Args:
            size (int): Bytes a leer, None para auto
            timeout (float): Timeout específico, None para usar adaptativo
            
        Returns:
            str: Datos leídos decodificados
        """
        if not self.connected:
            self.logger.error("Intento de lectura sin conexión activa")
            return ""
            
        if timeout is None:
            timeout = self._get_adaptive_timeout()
            
        start_time = time.time()
        response = []
        
        while (time.time() - start_time) < timeout:
            try:
                data = self._read_internal(size or 128)
                if data:
                    response.extend(data)
                    if b'>' in data:  # Prompt ELM327
                        break
            except Exception as e:
                self.logger.warning(f"Error de lectura: {e}")
                time.sleep(0.01)
                
        response_time = time.time() - start_time
        self._update_response_metrics(response_time)
        
        return bytes(response).decode('utf-8', errors='ignore')
        
    def _get_adaptive_timeout(self) -> float:
        """
        Calcula timeout adaptativo basado en historia de respuestas.
        
        Returns:
            float: Timeout calculado en segundos
        """
        if not self._response_times:
            return self.timeout
            
        # Usar percentil 95 + margen
        sorted_times = sorted(self._response_times)
        p95_idx = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_idx]
        
        return min(max(p95_time * 1.5, self.timeout), 10.0)  # Entre timeout base y 10s
        
    def _update_response_metrics(self, response_time: float):
        """
        Actualiza métricas de tiempo de respuesta.
        
        Args:
            response_time (float): Tiempo de respuesta en segundos
        """
        self._response_times.append(response_time)
        if len(self._response_times) > self._max_response_times:
            self._response_times.pop(0)
            
    def send_command(self, command: str, 
                    expected_response: Optional[str] = None,
                    custom_timeout: Optional[float] = None) -> Tuple[bool, str]:
        """
        Envía comando y lee respuesta con validación.
        
        Args:
            command (str): Comando a enviar
            expected_response (str): Respuesta esperada para validación
            custom_timeout (float): Timeout específico para este comando
            
        Returns:
            Tuple[bool, str]: (éxito, respuesta)
        """
        if not self.write(command):
            return False, ""
            
        response = self.read(timeout=custom_timeout)
        
        if expected_response and expected_response not in response:
            self.logger.warning(f"Respuesta no esperada. Esperado: {expected_response}, Recibido: {response}")
            return False, response
            
        return True, response
