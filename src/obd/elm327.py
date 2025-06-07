# Comunicación con ELM327
from .connection import OBDConnection
import time


class ELM327:
    """Clase para manejar la comunicación con el adaptador ELM327."""

    def __init__(self, connection: OBDConnection):
        self.connection = connection
        self._protocol = None
        self._initialized = False
        self._init_commands = [
            ("ATE0", "Echo Off"),
            ("ATL0", "Linefeeds Off"),
            ("ATH0", "Headers Off"),
            ("ATS0", "Spaces Off"),
            ("ATI", "Identificación"),
            ("ATSP0", "Protocolo Auto"),
        ]

    def initialize(self):
        """Inicializa el ELM327 con configuración básica."""
        if not self._reset_device():
            return False

        return self._configure_device()

    def _reset_device(self):
        """Resetea el dispositivo ELM327."""
        try:
            self.connection.write("ATZ\r")
            time.sleep(1)  # Espera necesaria post-reset
            resp = self.connection.read(128)
            return bool(resp and "ELM" in resp.upper())
        except (IOError, ConnectionError) as e:
            print(f"Error reseteando dispositivo: {str(e)}")
            return False

    def _configure_device(self):
        """Aplica la configuración inicial del dispositivo."""
        for cmd, desc in self._init_commands:
            if not self._send_init_command(cmd, desc):
                return False

        self._initialized = True
        return True

    def _send_init_command(self, cmd, desc):
        """Envía un comando de inicialización con reintentos."""
        for attempt in range(3):
            try:
                self.connection.write(f"{cmd}\r")
                time.sleep(0.1)
                resp = self.connection.read(128)

                if resp and ("OK" in resp.upper() or "ELM" in resp.upper()):
                    return True

                time.sleep(0.2)  # Espera extra entre intentos

            except (IOError, ConnectionError) as e:
                print(f"Error en {desc} (intento {attempt+1}): {str(e)}")

        print(f"Fallo en comando {desc}")
        return False

    def send_command(self, cmd):
        """Envía un comando al ELM327."""
        if not self._initialized and not self.initialize():
            return None

        try:
            self.connection.write(f"{cmd}\r")
            time.sleep(0.1)
            resp = self.connection.read(128)

            if resp and not any(x in resp for x in ["NO DATA", "ERROR"]):
                return resp

        except (IOError, ConnectionError):
            pass

        return None

    def is_initialized(self):
        """Retorna si el dispositivo está inicializado."""
        return self._initialized

    def current_protocol(self):
        """Retorna el protocolo actual."""
        return self._protocol

    def scan_supported_pids(self):
        """
        Escanea los PIDs soportados por la ECU.
        Retorna una lista de los PIDs detectados.
        """
        if not self._check_initialization():
            return []
            
        resp = self._get_supported_pids_response()
        if not resp:
            return []
            
        return self._parse_supported_pids(resp)
        
    def _check_initialization(self):
        """Verifica que el dispositivo esté inicializado."""
        return self._initialized or self.initialize()
        
    def _get_supported_pids_response(self):
        """Obtiene la respuesta de PIDs soportados."""
        try:
            return self.send_command("0100")
        except (IOError, ConnectionError) as e:
            print(f"Error solicitando PIDs: {str(e)}")
            return None
            
    def _parse_supported_pids(self, resp):
        """Parsea la respuesta de PIDs soportados."""
        supported_pids = []
        
        try:
            if not ("41 00" in resp or "4100" in resp):
                return supported_pids
                
            hex_data = self._extract_pid_data(resp)
            if not hex_data:
                return supported_pids
                
            bin_data = format(int(hex_data, 16), '032b')
            supported_pids = self._test_supported_pids(bin_data)
                
        except (IOError, ConnectionError, ValueError) as e:
            print(f"Error parseando PIDs: {str(e)}")
            
        return supported_pids
        
    def _extract_pid_data(self, resp):
        """Extrae los datos hexadecimales de la respuesta."""
        if "41 00" in resp:
            idx = resp.find("41 00") + 5
        else:
            idx = resp.find("4100") + 4
            
        return resp[idx:idx+8].replace(" ", "")
        
    def _test_supported_pids(self, bin_data):
        """Prueba cada PID marcado como soportado."""
        supported = []
        
        for i in range(32):
            if bin_data[i] == "1":
                pid = format(i + 1, '02x').upper()
                if self._test_single_pid(pid):
                    supported.append(pid)
                    
        return supported
        
    def _test_single_pid(self, pid):
        """Prueba un PID específico."""
        try:
            test_cmd = f"01{pid}"
            return bool(self.send_command(test_cmd))
        except (IOError, ConnectionError):
            return False
# Versión consolidada, métodos corregidos, 2025-06-03
