"""
Implementación de conexión OBD-II vía WiFi con manejo robusto.
"""
import socket
import logging
import time
from typing import Optional
from .connection_base import OBD2Connection, OBD2ConnectionError


class OBD2WiFiConnection(OBD2Connection):
    """
    Implementación WiFi de conexión OBD-II con reconexión automática.
    """
    
    def __init__(self, host: str = "192.168.0.10", port: int = 35000,
                 timeout: float = 2.0, retry_count: int = 3):
        """
        Inicializa conexión WiFi.
        
        Args:
            host: IP del adaptador ELM327
            port: Puerto TCP
            timeout: Timeout base
            retry_count: Número de reintentos
        """
        super().__init__(timeout=timeout, retry_count=retry_count)
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.logger = logging.getLogger(__name__)
        
    def _connect_internal(self) -> bool:
        """
        Establece conexión TCP.
        
        Returns:
            bool: True si conexión exitosa
        """
        try:
            if self.socket:
                self.socket.close()
                
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            # Test básico de conectividad
            self.socket.sendall(b'ATI\r')
            time.sleep(0.1)
            response = self.socket.recv(1024)
            
            if not response or b'ELM327' not in response:
                raise OBD2ConnectionError("No se detectó adaptador ELM327")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error conectando a {self.host}:{self.port} - {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            return False
            
    def _disconnect_internal(self):
        """Cierra conexión TCP."""
        if self.socket:
            try:
                self.socket.close()
            finally:
                self.socket = None
                
    def _write_internal(self, data: bytes) -> bool:
        """
        Envía datos por socket.
        
        Args:
            data: Datos a enviar
            
        Returns:
            bool: True si envío exitoso
        """
        if not self.socket:
            return False
            
        try:
            self.socket.sendall(data)
            return True
        except socket.error as e:
            self.logger.error(f"Error escribiendo en socket: {e}")
            return False
            
    def _read_internal(self, size: int) -> bytes:
        """
        Lee datos del socket.
        
        Args:
            size: Bytes a leer
            
        Returns:
            bytes: Datos leídos
        """
        if not self.socket:
            return b''
            
        try:
            return self.socket.recv(size)
        except socket.timeout:
            return b''
        except socket.error as e:
            self.logger.error(f"Error leyendo socket: {e}")
            return b''
            
    def reconnect(self) -> bool:
        """
        Intenta reconexión con backoff exponencial.
        
        Returns:
            bool: True si reconexión exitosa
        """
        for attempt in range(self.retry_count):
            self.logger.info(f"Intento de reconexión #{attempt + 1}")
            
            try:
                self.disconnect()
                if self._connect_internal():
                    self.logger.info("Reconexión exitosa")
                    return True
            except Exception as e:
                self.logger.error(f"Error en reconexión: {e}")
                
            # Backoff exponencial
            time.sleep(0.5 * (2 ** attempt))
            
        self.logger.error("Reconexión fallida después de todos los intentos")
        return False
