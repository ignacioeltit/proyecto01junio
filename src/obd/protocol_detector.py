"""
Modulo: protocol_detector.py
---------------------------
Autodetección de protocolo OBD-II compatible con ELM327 (WiFi/USB/Serial).

Este módulo permite detectar automáticamente el protocolo de comunicación OBD-II
usando comandos AT estándar (ATZ, ATSP 0, ATDP) y probar protocolos específicos.

Uso recomendado:
- Importar y crear una instancia de ProtocolDetector pasando una conexión ELM327 abierta.
- Llamar a detect() para autodetectar el protocolo y verificar comunicación.
- Integrar el resultado en el dashboard o backend de la app.

Autor: Equipo Inteligencia Automotriz
Fecha: 2025-06-05
"""

import time

class ProtocolDetector:
    """
    Clase para autodetección de protocolo OBD-II usando ELM327.
    Compatible con conexiones WiFi, USB o Serial.
    """
    PROTOCOL_LIST = [
        ("AUTO", 0),     # ATSP0: Automático
        ("CAN_11B_500K", 6),  # ATSP6: CAN 11 bits 500Kbps
        ("ISO9141", 3),  # ATSP3: ISO 9141-2
        ("KWP2000", 4),  # ATSP4: ISO 14230-4 (KWP2000)
        ("J1850PWM", 1), # ATSP1: SAE J1850 PWM
        ("J1850VPW", 2)  # ATSP2: SAE J1850 VPW
    ]
    TEST_PID = "0100"  # PID estándar para prueba de comunicación

    def __init__(self, connection):
        """
        connection: objeto con métodos send_command(cmd:str) y read_response(timeout:float)
        """
        self.conn = connection
        self.last_protocol = None
        self.last_response = None

    def detect(self):
        """
        Autodetecta el protocolo OBD-II y verifica comunicación básica.
        Devuelve (nombre_protocolo, exito:bool, respuesta:str)
        """
        self._reset_adapter()
        # 1. Intentar autodetección (ATSP0)
        if self._test_protocol(0):
            proto = self._get_protocol_name()
            return proto, True, self.last_response
        # 2. Intentar protocolos específicos
        for proto_name, proto_code in self.PROTOCOL_LIST[1:]:
            if self._test_protocol(proto_code):
                return proto_name, True, self.last_response
        return "UNKNOWN", False, self.last_response

    def _reset_adapter(self):
        self.conn.send_command("ATZ")
        time.sleep(2)
        self.conn.clear_buffer()

    def _test_protocol(self, proto_code):
        self.conn.send_command(f"ATSP{proto_code}")
        time.sleep(1)
        self.conn.send_command(self.TEST_PID)
        resp = self.conn.read_response(timeout=3)
        self.last_response = resp
        return self._is_valid_response(resp)

    def _get_protocol_name(self):
        self.conn.send_command("ATDP")
        proto = self.conn.read_response(timeout=2)
        self.last_protocol = proto.strip()
        return self.last_protocol

    @staticmethod
    def _is_valid_response(resp):
        if not resp:
            return False
        clean = resp.replace(" ", "").upper()
        if "NODATA" in clean or "ERROR" in clean:
            return False
        # Respuesta válida típica: empieza con '41' o '7E8'
        return clean.startswith("41") or clean.startswith("7E8")

# Ejemplo de uso (en test o integración):
# from protocol_detector import ProtocolDetector
# detector = ProtocolDetector(connection)
# proto, ok, resp = detector.detect()
# print(f"Protocolo detectado: {proto}, éxito: {ok}, respuesta: {resp}")
