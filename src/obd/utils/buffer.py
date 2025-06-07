"""
Implementación de buffer circular para manejo robusto de comunicación OBD-II.
"""
from collections import deque
import threading

class CircularBuffer:
    def __init__(self, max_size=1024):
        """
        Inicializa un buffer circular thread-safe para datos OBD-II.
        
        Args:
            max_size (int): Tamaño máximo del buffer en bytes
        """
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.max_size = max_size
        
    def write(self, data: bytes):
        """
        Escribe datos al buffer de forma thread-safe.
        
        Args:
            data (bytes): Datos a escribir
        """
        with self.lock:
            for byte in data:
                self.buffer.append(byte)
                
    def read(self, size: int = None) -> bytes:
        """
        Lee datos del buffer de forma thread-safe.
        
        Args:
            size (int): Cantidad de bytes a leer. Si None, lee todo.
            
        Returns:
            bytes: Datos leídos
        """
        with self.lock:
            if size is None:
                size = len(self.buffer)
                
            if size > len(self.buffer):
                size = len(self.buffer)
                
            result = bytes(list(self.buffer)[:size])
            for _ in range(size):
                self.buffer.popleft()
            return result
            
    def clear(self):
        """Limpia el buffer."""
        with self.lock:
            self.buffer.clear()
            
    def available(self) -> int:
        """
        Retorna la cantidad de bytes disponibles para lectura.
        
        Returns:
            int: Número de bytes disponibles
        """
        with self.lock:
            return len(self.buffer)
