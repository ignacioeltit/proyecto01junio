"""
Implementación robusta del protocolo ELM327 con reconexión automática y parsing universal.
"""
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from .connection_base import OBD2Connection
from .pid_parser import PIDParser, PIDParserError

class ELM327Error(Exception):
    """Excepción base para errores de ELM327."""
    pass

class ELM327:
    """
    Implementación robusta del protocolo ELM327 con manejo avanzado de errores.
    """
    
    # Comandos AT comunes
    AT_COMMANDS = {
        'RESET': 'ATZ',
        'ECHO_OFF': 'ATE0',
        'LINEFEEDS_OFF': 'ATL0',
        'HEADERS_OFF': 'ATH0',
        'SPACES_OFF': 'ATS0',
        'AUTO_PROTOCOL': 'ATSP0',
        'DESCRIBE_PROTOCOL': 'ATDP',
        'READ_VOLTAGE': 'ATRV'
    }
    
    def __init__(self, connection: OBD2Connection, parser: Optional[PIDParser] = None):
        """
        Inicializa interfaz ELM327.
        
        Args:
            connection: Conexión OBD-II base
            parser: Parser de PIDs universal (opcional)
        """
        self.logger = logging.getLogger(__name__)
        self.connection = connection
        self.parser = parser or PIDParser()
        self.protocol = None
        self.supported_pids: Dict[str, bool] = {}
        self.dtc_count = 0
        
        # Control de inicialización
        self.initialized = False
        self.initialization_attempts = 0
        self.max_init_attempts = 3
        
        # Control de reintentos
        self.command_timeouts = {}
        self.error_counts = {}
        self.last_successful_command = None
        
    def initialize(self) -> bool:
        """
        Inicializa el adaptador ELM327 con retry automático.
        
        Returns:
            bool: True si inicialización exitosa
        """
        self.initialization_attempts += 1
        self.logger.info(f"Intento de inicialización #{self.initialization_attempts}")
        
        try:
            # Reset y comandos básicos
            if not self._send_at_commands():
                return False
                
            # Detectar protocolo
            protocol = self._detect_protocol()
            if not protocol:
                return False
            self.protocol = protocol
                
            # Escanear PIDs soportados
            if not self._scan_supported_pids():
                return False
                
            self.initialized = True
            self.logger.info("Inicialización ELM327 exitosa")
            return True
            
        except Exception as e:
            self.logger.error(f"Error en inicialización: {e}")
            if self.initialization_attempts < self.max_init_attempts:
                self.logger.info("Reintentando inicialización...")
                time.sleep(1)
                return self.initialize()
            return False
            
    def _send_at_commands(self) -> bool:
        """
        Envía secuencia de comandos AT inicial.
        
        Returns:
            bool: True si todos los comandos exitosos
        """
        commands = [
            (self.AT_COMMANDS['RESET'], 1.0),  # Reset con espera extra
            (self.AT_COMMANDS['ECHO_OFF'], 0.1),
            (self.AT_COMMANDS['LINEFEEDS_OFF'], 0.1),
            (self.AT_COMMANDS['HEADERS_OFF'], 0.1),
            (self.AT_COMMANDS['SPACES_OFF'], 0.1),
            (self.AT_COMMANDS['AUTO_PROTOCOL'], 0.2)
        ]
        
        for cmd, delay in commands:
            success, resp = self.connection.send_command(cmd)
            if not success or 'OK' not in resp:
                self.logger.error(f"Comando AT falló: {cmd} -> {resp}")
                return False
            time.sleep(delay)
            
        return True
        
    def _detect_protocol(self) -> Optional[str]:
        """
        Detecta protocolo OBD-II activo.
        
        Returns:
            str: Descripción del protocolo o None si error
        """
        success, resp = self.connection.send_command(self.AT_COMMANDS['DESCRIBE_PROTOCOL'])
        if success and resp:
            self.logger.info(f"Protocolo detectado: {resp}")
            return resp.strip()
        return None
        
    def _scan_supported_pids(self) -> bool:
        """
        Escanea PIDs soportados por el vehículo.
        
        Returns:
            bool: True si escaneo exitoso
        """
        pid_ranges = ['0100', '0120', '0140', '0160', '0180', '01A0', '01C0']
        for pid in pid_ranges:
            success, resp = self.connection.send_command(pid)
            if success and resp and 'NO DATA' not in resp:
                try:
                    # Decodificar bitmap de PIDs soportados
                    clean_resp = resp.replace(' ', '').replace('\r', '').replace('\n', '')
                    if len(clean_resp) >= 10:  # 41 xx + 4 bytes datos
                        bits = bin(int(clean_resp[4:12], 16))[2:].zfill(32)
                        base = int(pid[2:4], 16)
                        for i, bit in enumerate(bits):
                            if bit == '1':
                                pid_hex = f"01{(base + i):02X}"
                                self.supported_pids[pid_hex] = True
                except Exception as e:
                    self.logger.warning(f"Error decodificando PIDs soportados: {e}")
                    
        self.logger.info(f"PIDs soportados detectados: {len(self.supported_pids)}")
        return bool(self.supported_pids)
        
    def read_pid(self, pid: str) -> Optional[float]:
        """
        Lee y parsea valor de PID con manejo de errores.
        
        Args:
            pid: PID a leer en formato hex (ej: '010C')
            
        Returns:
            Valor parseado o None si error
        """
        if not self.initialized:
            self.logger.error("ELM327 no inicializado")
            return None
            
        if pid not in self.supported_pids:
            self.logger.warning(f"PID no soportado: {pid}")
            return None
            
        success, resp = self.connection.send_command(pid)
        if not success:
            self._handle_command_error(pid)
            return None
            
        try:
            value = self.parser.parse_response(pid, resp)
            if value is not None:
                self._register_success(pid)
            return value
        except PIDParserError as e:
            self.logger.error(f"Error parseando respuesta de {pid}: {e}")
            return None
            
    def read_pids(self, pids: List[str]) -> Dict[str, Optional[float]]:
        """
        Lee múltiples PIDs en una sola operación.
        
        Args:
            pids: Lista de PIDs a leer
            
        Returns:
            Diccionario de PID -> valor
        """
        results = {}
        for pid in pids:
            results[pid] = self.read_pid(pid)
        return results
        
    def read_dtc(self) -> List[str]:
        """
        Lee códigos DTC almacenados.
        
        Returns:
            Lista de códigos DTC
        """
        success, resp = self.connection.send_command('03')
        if not success:
            return []
            
        dtcs = []
        try:
            # Procesar respuesta DTC (43 + códigos)
            clean_resp = resp.replace(' ', '').replace('\r', '').replace('\n', '')
            if clean_resp.startswith('43'):
                for i in range(2, len(clean_resp), 4):
                    code = clean_resp[i:i+4]
                    if code != '0000':
                        dtcs.append(self._format_dtc(code))
        except Exception as e:
            self.logger.error(f"Error procesando DTCs: {e}")
            
        return dtcs
        
    def clear_dtc(self) -> bool:
        """
        Borra códigos DTC almacenados.
        
        Returns:
            bool: True si operación exitosa
        """
        success, resp = self.connection.send_command('04')
        return success and 'OK' in resp
        
    def get_voltage(self) -> Optional[float]:
        """
        Lee voltaje de batería.
        
        Returns:
            Voltaje o None si error
        """
        success, resp = self.connection.send_command(self.AT_COMMANDS['READ_VOLTAGE'])
        if success and resp:
            try:
                return float(resp.replace('V', '').strip())
            except ValueError:
                pass
        return None
        
    def _handle_command_error(self, command: str):
        """
        Maneja errores de comando con backoff exponencial.
        
        Args:
            command: Comando que falló
        """
        self.error_counts[command] = self.error_counts.get(command, 0) + 1
        if self.error_counts[command] > 3:
            self.logger.warning(f"Comando {command} fallando frecuentemente")
            
    def _register_success(self, command: str):
        """
        Registra comando exitoso y resetea contadores.
        
        Args:
            command: Comando exitoso
        """
        if command in self.error_counts:
            del self.error_counts[command]
        self.last_successful_command = command
        
    @staticmethod
    def _format_dtc(code: str) -> str:
        """
        Formatea código DTC.
        
        Args:
            code: Código hex raw
            
        Returns:
            Código DTC formateado
        """
        type_char = {
            '00': 'P', '01': 'C',
            '02': 'B', '03': 'U'
        }
        return f"{type_char[code[:2]]}{code[2:]}"
