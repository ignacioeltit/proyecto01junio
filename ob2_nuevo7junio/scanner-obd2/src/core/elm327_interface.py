"""
elm327_interface.py - Manejo de la conexión y comunicación con ELM327 WiFi (TCP/IP)
"""
import socket
import time
import logging
from typing import Optional
import random
import json
import os

class ELM327Interface:
    def __init__(self, ip: str = "192.168.0.10", port: int = 35000, timeout: float = 5.0, max_retries: int = 3, mode: str = "real"):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.max_retries = max_retries
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.logger = logging.getLogger("ELM327Interface")
        self.mode = mode  # "real" o "emulador"
        # Cargar PIDs si es emulador
        self._pid_defs = None
        if self.mode == "emulador":
            pid_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "pid_definitions.json")
            try:
                with open(pid_path, "r", encoding="utf-8") as f:
                    self._pid_defs = json.load(f)
            except Exception as e:
                self._pid_defs = {}
                print(f"[EMULADOR] No se pudo cargar pid_definitions.json: {e}")

    def connect(self) -> bool:
        if self.mode == "emulador":
            self.logger.info("Conexión en modo emulador/demo.")
            self.connected = True
            return True
        self.logger.info(f"Intentando conectar a ELM327 WiFi en {self.ip}:{self.port}")
        tries = 0
        while tries < self.max_retries:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect((self.ip, self.port))
                self.logger.info("Conexión TCP/IP establecida con éxito.")
                # Secuencia de comandos AT igual al test exitoso
                handshake_cmds = [
                    ("ATZ", "Reset ELM327"),
                    ("ATE0", "Desactivar eco"),
                    ("ATI", "Identificar dispositivo"),
                    ("0100", "Leer PIDs soportados")
                ]
                for cmd, label in handshake_cmds:
                    print(f"➡️ Enviando {label}: {cmd}")
                    self.sock.send((cmd + "\r").encode())
                    time.sleep(1)
                    try:
                        response = self.sock.recv(4096).decode(errors='ignore').strip()
                    except Exception:
                        response = ''
                    print(f"⬅️ Respuesta: {response if response else '[Sin respuesta]'}")
                    if cmd == "ATZ" and (not response or "ELM327" not in response and "OBDII" not in response):
                        self.logger.error("No se detectó ELM327 tras ATZ")
                        print("[ERROR] No se detectó ELM327 tras ATZ")
                        self.close()
                        raise Exception("No ELM327 after ATZ")
                    if cmd == "0100" and (not response or ("41 00" not in response and "4100" not in response)):
                        self.logger.error("No hay comunicación con la ECU tras 0100")
                        print("[ERROR] No hay comunicación con la ECU tras 0100")
                        self.close()
                        raise Exception("No ECU after 0100")
                self.connected = True
                return True
            except Exception as e:
                self.logger.error(f"Error de conexión: {e}")
                print(f"[ERROR] Error de conexión: {e}")
                self.close()
            tries += 1
            self.logger.warning(f"Reintentando conexión ({tries}/{self.max_retries})...")
            time.sleep(1)
        self.connected = False
        return False

    def _handshake(self) -> bool:
        """Realiza el handshake AT y verifica comunicación con ELM327 y ECU"""
        handshake_cmds = [
            ("ATZ", 2), ("ATE0", 0.3), ("ATL0", 0.3), ("ATS0", 0.3), ("ATH0", 0.3), ("ATSP0", 0.5), ("0100", 1)
        ]
        for cmd, wait in handshake_cmds:
            resp = self.send_command(cmd)
            self.logger.debug(f"Comando: {cmd} | Respuesta: {resp.strip() if resp else 'N/A'}")
            time.sleep(wait)
            if cmd == "ATZ" and (not resp or "ELM327" not in resp):
                self.logger.error("No se detectó ELM327 tras ATZ")
                return False
            if cmd == "0100" and (not resp or ("41 00" not in resp and "4100" not in resp)):
                self.logger.error("No hay comunicación con la ECU tras 0100")
                return False
        return True

    def send_command(self, cmd: str) -> str:
        if self.mode == "emulador":
            return self._emulate_response(cmd)
        if not self.connected or not self.sock:
            self.logger.error("No conectado a ELM327 WiFi")
            return ""
        try:
            self.sock.send((cmd.strip() + "\r").encode())
            # Solo esperar 0.08s para lectura de PIDs (rápido)
            time.sleep(0.08)
            data = b""
            try:
                data = self.sock.recv(4096)
            except Exception:
                pass
            resp = data.decode(errors="ignore") if data else ''
            self.logger.info(f"Comando enviado: {cmd.strip()} | Respuesta: {resp.strip()}")
            return resp
        except Exception as e:
            self.logger.error(f"Error enviando comando '{cmd}': {e}")
            return ""

    def _emulate_response(self, cmd: str) -> str:
        """Simula respuestas OBD-II para pruebas/demo, usando la biblioteca de PIDs."""
        if cmd.startswith("AT"):
            return "OK>"
        if cmd.replace(" ","") == "0902":
            # Simular VIN válido (17 caracteres hex)
            # Formato OBD: 49 02 01 XX XX XX XX 49 02 02 XX XX XX XX 49 02 03 XX XX XX XX
            vin_ascii = "1HGBH41JXMN109186"  # Ejemplo VIN
            vin_bytes = [f"{ord(c):02X}" for c in vin_ascii]
            # Dividir en bloques de 4
            bloques = [vin_bytes[i:i+4] for i in range(0, len(vin_bytes), 4)]
            resp = ""
            for idx, bloque in enumerate(bloques):
                resp += f"49 02 {idx+1:02X} " + " ".join(bloque) + " "
            return resp.strip() + ">"
        if self._pid_defs and cmd in self._pid_defs:
            pid_info = self._pid_defs[cmd]
            # Determinar cantidad de bytes de datos según la fórmula (A, B, C, D...)
            formula = pid_info.get("formula", "A")
            # Contar cuántas letras mayúsculas distintas hay en la fórmula (A, B, C, D...)
            import re
            bytes_needed = max([ord(x)-ord('A')+1 for x in re.findall(r"[A-F]", formula)] or [1])
            # Generar valor aleatorio dentro del rango
            min_v = pid_info.get("min", 0)
            max_v = pid_info.get("max", 255)
            valor = random.uniform(min_v, max_v)
            # Invertir la fórmula para obtener los bytes (solo para fórmulas simples)
            # Por defecto: poner el valor en A, B, ...
            data_bytes = []
            if bytes_needed == 2 and "+" in formula and "/" in formula:
                # Fórmulas tipo ((A*256)+B)/X
                val = int(valor * 4) if "/4" in formula else int(valor)
                A = (val >> 8) & 0xFF
                B = val & 0xFF
                data_bytes = [A, B]
            elif bytes_needed == 2:
                val = int(valor)
                A = (val >> 8) & 0xFF
                B = val & 0xFF
                data_bytes = [A, B]
            elif bytes_needed == 1:
                data_bytes = [int(valor)]
            else:
                # Para más de 2 bytes, repartir el valor
                v = int(valor)
                data_bytes = [(v >> (8*i)) & 0xFF for i in reversed(range(bytes_needed))]
            # Construir respuesta OBD-II: 41 XX [data bytes]>
            pid_hex = cmd[2:]
            resp = f"41{pid_hex}" + "".join(f"{b:02X}" for b in data_bytes) + ">"
            return resp
        # Respuesta por defecto para PIDs no definidos
        return "NO DATA>"

    def close(self):
        if self.sock:
            try:
                self.sock.close()
                self.logger.info("Conexión TCP/IP cerrada correctamente")
            except Exception as e:
                self.logger.error(f"Error al cerrar socket: {e}")
            finally:
                self.sock = None
        self.connected = False

    def query(self, cmd: str) -> str:
        """Alias para send_command, usado por la GUI para compatibilidad."""
        return self.send_command(cmd)
