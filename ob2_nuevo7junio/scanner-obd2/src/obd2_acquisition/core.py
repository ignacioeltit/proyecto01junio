"""
core.py - Lógica principal de adquisición OBD-II real
"""
import asyncio
import logging
import serial_asyncio
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime

class OBD2Acquisition:
    """
    Clase profesional para adquisición de datos OBD-II reales desde la ECU.
    """
    def __init__(self, port, baudrate=38400, timeout=1.0, logger=None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.logger = logger or logging.getLogger("obd2_acquisition")
        self.reader = None
        self.writer = None
        self.connected = False
        self.tuning_pids = []
        self.tuning_callback = None
        self.tuning_session_id = None
        self.tuning_map_version = None
        self.tuning_logfile = None
        self.tuning_logger = None

    async def connect(self):
        self.reader, self.writer = await serial_asyncio.open_serial_connection(
            url=self.port, baudrate=self.baudrate)
        self.connected = True
        self.logger.info(f"Conectado a {self.port} @ {self.baudrate}bps")

    async def disconnect(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False
        self.logger.info("Desconectado")

    async def send_command(self, cmd):
        if not self.connected:
            raise RuntimeError("No conectado al dispositivo OBD-II")
        self.writer.write((cmd + "\r").encode())
        await self.writer.drain()
        resp = await self.reader.readline()
        return resp.decode(errors="ignore").strip()

    async def get_supported_pids(self):
        resp = await self.send_command("0100")
        # Aquí puedes parsear la respuesta según el protocolo OBD-II
        return resp

    async def read_pids(self, pid_list):
        results = {}
        for pid in pid_list:
            resp = await self.send_command(pid)
            results[pid] = resp
        return results

    async def read_vin_iso_tp(self):
        """Lee el VIN usando el comando estándar OBD-II 09 02 (modo 09 PID 02)."""
        if not self.connected:
            raise RuntimeError("No conectado al dispositivo OBD-II")
        # Usar send_command para enviar y recibir la respuesta
        resp = await self.send_command("09 02")
        # Procesar la respuesta para extraer el VIN
        vin = ''
        # Buscar secuencias hexadecimales en la respuesta
        import re
        hex_bytes = re.findall(r'([0-9A-Fa-f]{2})', resp)
        # El VIN suele estar en los últimos 17 caracteres ASCII válidos
        ascii_chars = [chr(int(b, 16)) for b in hex_bytes if 32 <= int(b, 16) <= 126]
        vin = ''.join(ascii_chars)
        # Limitar a 17 caracteres típicos de VIN
        return vin.strip()[:17]

    async def read_vin_at(self):
        """Stub para compatibilidad: fallback de lectura de VIN por AT (no implementado en hardware real)."""
        return None

    def subscribe_tuning_pids(self, pid_list, session_id, map_version, callback=None):
        self.tuning_pids = pid_list
        self.tuning_callback = callback
        self.tuning_session_id = session_id
        self.tuning_map_version = map_version
        # Configura logger rotativo JSON lines
        log_path = f"tuning_{session_id}_{datetime.now().strftime('%Y%m%d')}.log"
        self.tuning_logfile = log_path
        self.tuning_logger = logging.getLogger(f"tuning.{session_id}")
        handler = RotatingFileHandler(log_path, maxBytes=2*1024*1024, backupCount=5)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.tuning_logger.handlers = []
        self.tuning_logger.addHandler(handler)
        self.tuning_logger.setLevel(logging.INFO)

    async def read_tuning_loop(self, vin, make, model):
        """Loop asíncrono para leer y emitir datos de tuning."""
        try:
            while self.connected and self.tuning_pids:
                try:
                    results = await self.read_pids(self.tuning_pids)
                    # Decodifica y estructura los datos
                    pid_values = {pid: results.get(pid, None) for pid in self.tuning_pids}
                    # Ejemplo de campos críticos
                    log_data = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": "INFO",
                        "module": "tuning",
                        "session_id": self.tuning_session_id,
                        "map_version": self.tuning_map_version,
                        "VIN": vin,
                        "make": make,
                        "model": model,
                        # ...agrega aquí el mapeo de cada PID crítico...
                        **pid_values,
                        "flags": {"WOT": False, "fallback": False, "knock_detected": False}
                    }
                    self.tuning_logger.info(json.dumps(log_data))
                    if self.tuning_callback:
                        self.tuning_callback(self.tuning_session_id, self.tuning_map_version, pid_values)
                except Exception as ex:
                    self.tuning_logger.exception("Error en read_tuning_loop")
                await asyncio.sleep(0.3)
        except Exception as e:
            self.tuning_logger.exception("Fallo en loop principal de tuning")
