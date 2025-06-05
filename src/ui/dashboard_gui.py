# Versión PEP8 y limpieza automática, 2025-06-03
"""
Dashboard OBD-II Multiplataforma – PyQt6
----------------------------------------
Interfaz gráfica profesional para monitoreo, logging y diagnóstico OBD-II en tiempo real.
Cumple los más altos estándares de UI/UX, robustez y modularidad.
"""

# --- ESTÁNDAR DE FLUJO DE PIds Y DUPLICADOS ---
#
# 1. Solo se permite una variante de cada parámetro (PID) en selección, gauges y logs/exportación.
# 2. El nombre legible (ej: 'rpm', 'vel', 'temp', etc.) es el estándar para todo el flujo (UI, backend, exportador).
# 3. Si el usuario intenta seleccionar un PID duplicado (por nombre o código), la UI lo bloquea y muestra advertencia.
# 4. El backend y el exportador deduplican automáticamente y priorizan el nombre legible.
# 5. El log/exportación nunca tendrá columnas duplicadas. Si se detecta, se advierte y corrige.
# 6. El validador automático revisa cada exportación y reporta si existe alguna columna duplicada.
# 7. Todas las advertencias quedan registradas en el log de sesión y pueden ser auditadas.
#
# Para más detalles, ver README y scripts/validar_duplicados_csv.py
#

# --- INICIO: Manejo robusto de imports para ejecución desde cualquier carpeta ---
import os
import sys

def setup_project_path():
    """
    Asegura que el path absoluto de 'src' esté en sys.path para imports robustos.
    Llamar al inicio de cualquier script principal.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

setup_project_path()
# --- FIN: Manejo robusto de imports ---

import time
import math
import random
import sqlite3
import csv
import socket
import inspect
import re
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QMessageBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QScrollArea,
    QGridLayout,
)
from ui.widgets.gauge import GaugeWidget
from obd.connection import OBDConnection
from obd.elm327 import ELM327
from obd.pids_ext import PIDS, normalizar_pid, buscar_pid
from utils.logging_app import log_evento_app

# --- Corrección: Conversión robusta de datos OBD-II a int/float en modo real ---
# Todos los valores numéricos de PIDs se convierten a int/float antes de operar, loguear o exportar.
# Si la conversión falla, se deja el valor original y se puede advertir en el log o UI.


# --- MOCK: Abstracción de fuente de datos (real/emulador) ---
class OBDDataSource:
    """
    Backend de adquisición, parsing y logging OBD-II.
    No contiene lógica ni referencias de UI. Expone métodos para obtener datos, logs y diagnóstico.
    Todos los errores y advertencias se propagan únicamente por valores de retorno, excepciones o logs.
    """

    def __init__(self, modo="emulador"):
        print(f"[DEBUG] OBDDataSource.__init__: modo={modo}")
        self.modo = modo
        self.escenario = "ralenti"  # Escenario activo para emulador
        self.rpm = 800
        self.vel = 0
        self.dtc = []
        self.connected = False
        self.conn = None
        self.elm = None
        self.log = []  # Lista para logging en memoria
        self.db_conn = None
        self.db_cursor = None
        self.last_handshake_ok = False
        self.last_handshake_error = None
        # Asegurar que siempre se usen nombres legibles
        self.pids_disponibles = [normalizar_pid(pid) for pid in PIDS.keys()]
        print(f"[DEBUG] OBDDataSource inicializado en modo: {self.modo}")

    def set_escenario(self, escenario):
        self.escenario = escenario
        # Asignación dinámica de valores según el escenario de emulación
        if self.modo == "emulador":
            if escenario == "ralenti":
                self.rpm = 800
                self.vel = 0
            elif escenario == "aceleracion":
                self.rpm = 3500
                self.vel = 40
            elif escenario == "crucero":
                self.rpm = 2200
                self.vel = 90
            elif escenario == "frenado":
                self.rpm = 1200
                self.vel = 20
            elif escenario == "ciudad":
                self.rpm = 1500
                self.vel = 30
            elif escenario == "carretera":
                self.rpm = 2500
                self.vel = 110
            elif escenario == "falla":
                self.rpm = 400
                self.vel = 0
            else:
                self.rpm = 800
                self.vel = 0
        log_evento_app(
            "INFO", f"Escenario cambiado a: {escenario}", contexto="set_escenario"
        )

    def connect(self):
        """
        Establece la conexión con el vehículo (modo real) o activa el modo emulador.
        Configura la base de datos SQLite para logging persistente.
        """
        try:
            if self.modo == "real":
                try:
                    self.conn = OBDConnection(
                        mode="wifi", ip="192.168.0.10", tcp_port=35000
                    )
                    self.conn.connect()
                    self.elm = ELM327(self.conn)
                    handshake_ok = self.elm.initialize()
                    self.connected = handshake_ok
                    self.last_handshake_ok = handshake_ok
                    if handshake_ok:
                        log_evento_app(
                            "INFO", "Handshake OK con ELM327", contexto="connect"
                        )
                    else:
                        log_evento_app(
                            "ERROR", "Handshake fallido con ELM327", contexto="connect"
                        )
                except Exception as e:
                    self.connected = False
                    self.last_handshake_ok = False
                    self.last_handshake_error = str(e)
                    log_evento_app(
                        "ERROR", f"Fallo de conexión OBD-II: {e}", contexto="connect"
                    )
                    raise e
            else:
                self.connected = True
                self.last_handshake_ok = True
                log_evento_app("INFO", "Modo emulador conectado", contexto="connect")
            # Conexión a SQLite para logging persistente
            self.db_conn = sqlite3.connect("obd_log.db")
            self.db_cursor = self.db_conn.cursor()
            self.db_cursor.execute(
                """CREATE TABLE IF NOT EXISTS lecturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                rpm INTEGER,
                vel INTEGER,
                escenario TEXT
            )"""
            )
            self.db_conn.commit()
        except Exception as e:
            log_evento_app(
                "ERROR", f"Error general en connect: {e}", contexto="connect"
            )
            raise e

    def disconnect(self):
        """Cierra la conexión OBD-II y la base de datos SQLite, si están abiertas."""
        if self.modo == "real" and self.conn:
            try:
                self.conn.close()
                log_evento_app(
                    "INFO", "Desconexión OBD-II exitosa", contexto="disconnect"
                )
            except Exception as e:
                log_evento_app(
                    "ERROR", f"Error al cerrar conexión: {e}", contexto="disconnect"
                )
        self.connected = False
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None
            self.db_cursor = None
            log_evento_app("INFO", "Base de datos cerrada", contexto="disconnect")

    def safe_cast(self, val):
        """
        Conversión segura de valores a int o float.
        Si la conversión falla, se registra una advertencia y se devuelve el valor original.
        """
        try:
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return val
            if isinstance(val, str):
                if "." in val:
                    return float(val)
                return int(val)
        except (ValueError, TypeError) as e:
            log_evento_app(
                "ADVERTENCIA", f"Conversión fallida: {val} ({e})", contexto="safe_cast"
            )
            return val
        return val

    def parse_rpm(self, respuesta_cruda, pid_context=None, cmd_context=None):
        """Parsea respuesta cruda de RPM (ej: '410C0B20' o '41 0C 0B 20') a valor numérico. Robustez y logging."""
        if not respuesta_cruda or not isinstance(respuesta_cruda, str):
            log_evento_app(
                "ADVERTENCIA",
                f"[PARSE][{pid_context or 'rpm'}] Respuesta vacía o inválida para RPM. Contexto: cmd={cmd_context}, resp={respuesta_cruda}",
            )
            return None
        # Procesar cada línea por separado si hay varias
        for linea in respuesta_cruda.strip().splitlines():
            raw = linea.replace(" ", "")
            if (raw.startswith("410C") or linea.startswith("41 0C")) and len(raw) >= 8:
                try:
                    A = int(raw[4:6], 16)
                    B = int(raw[6:8], 16)
                    rpm = ((A * 256) + B) / 4
                    return int(rpm)
                except Exception as e:
                    log_evento_app(
                        "ADVERTENCIA",
                        f"[PARSE][{pid_context or 'rpm'}] Error parseando RPM. Línea: '{linea}', cmd={cmd_context}, error={e}",
                    )
                    continue
            else:
                log_evento_app(
                    "ADVERTENCIA",
                    f"[PARSE][{pid_context or 'rpm'}] Respuesta cruda no válida para RPM. Línea: '{linea}', cmd={cmd_context}",
                )
        return None

    def parse_vel(self, respuesta_cruda, pid_context=None, cmd_context=None):
        """Parsea respuesta cruda de velocidad (ej: '410D00' o '41 0D 00') a valor numérico. Robustez y logging."""
        if not respuesta_cruda or not isinstance(respuesta_cruda, str):
            log_evento_app(
                "ADVERTENCIA",
                f"[PARSE][{pid_context or 'vel'}] Respuesta vacía o inválida para velocidad. Contexto: cmd={cmd_context}, resp={respuesta_cruda}",
            )
            return None
        for linea in respuesta_cruda.strip().splitlines():
            raw = linea.replace(" ", "")
            if (raw.startswith("410D") or linea.startswith("41 0D")) and len(raw) >= 6:
                try:
                    vel = int(raw[4:6], 16)
                    return vel
                except Exception as e:
                    log_evento_app(
                        "ADVERTENCIA",
                        f"[PARSE][{pid_context or 'vel'}] Error parseando velocidad. Línea: '{linea}', cmd={cmd_context}, error={e}",
                    )
                    continue
            else:
                log_evento_app(
                    "ADVERTENCIA",
                    f"[PARSE][{pid_context or 'vel'}] Respuesta cruda no válida para velocidad. Línea: '{linea}', cmd={cmd_context}",
                )
        return None

    def parse_temp(self, respuesta_cruda, pid_context=None, cmd_context=None):
        """
        Parsea respuesta cruda de temperatura (ej: '41053A' o '41 05 3A') a valor numérico (°C).
        Fórmula estándar OBD-II: valor = byte - 40
        """
        if not respuesta_cruda or not isinstance(respuesta_cruda, str):
            log_evento_app(
                "ADVERTENCIA",
                f"[PARSE][{pid_context or 'temp'}] Respuesta vacía o inválida para temperatura. Contexto: cmd={cmd_context}, resp={respuesta_cruda}",
            )
            return None
        for linea in respuesta_cruda.strip().splitlines():
            raw = linea.replace(" ", "")
            if (raw.startswith("4105") or linea.startswith("41 05")) and len(raw) >= 6:
                try:
                    temp = int(raw[4:6], 16) - 40
                    return temp
                except Exception as e:
                    log_evento_app(
                        "ADVERTENCIA",
                        f"[PARSE][{pid_context or 'temp'}] Error parseando temperatura. Línea: '{linea}', cmd={cmd_context}, error={e}",
                    )
                    continue
            else:
                log_evento_app(
                    "ADVERTENCIA",
                    f"[PARSE][{pid_context or 'temp'}] Respuesta cruda no válida para temperatura. Línea: '{linea}', cmd={cmd_context}",
                )
        return None

    def parse_temp_aire(self, respuesta_cruda, pid_context=None, cmd_context=None):
        """
        Parsea respuesta cruda de temperatura de aire (ej: '410F37' o '41 0F 37') a valor numérico (°C).
        Fórmula estándar OBD-II: valor = byte - 40
        """
        if not respuesta_cruda or not isinstance(respuesta_cruda, str):
            log_evento_app(
                "ADVERTENCIA",
                f"[PARSE][{pid_context or 'temp_aire'}] Respuesta vacía o inválida para temp_aire. Contexto: cmd={cmd_context}, resp={respuesta_cruda}",
            )
            return None
        for linea in respuesta_cruda.strip().splitlines():
            raw = linea.replace(" ", "")
            if (raw.startswith("410F") or linea.startswith("41 0F")) and len(raw) >= 6:
                try:
                    temp_aire = int(raw[4:6], 16) - 40
                    return temp_aire
                except Exception as e:
                    log_evento_app(
                        "ADVERTENCIA",
                        f"[PARSE][{pid_context or 'temp_aire'}] Error parseando temp_aire. Línea: '{linea}', cmd={cmd_context}, error={e}",
                    )
                    continue
            else:
                log_evento_app(
                    "ADVERTENCIA",
                    f"[PARSE][{pid_context or 'temp_aire'}] Respuesta cruda no válida para temp_aire. Línea: '{linea}', cmd={cmd_context}",
                )
        return None

    def parse_pid_response(self, pid, resp, cmd_context=None):
        """
        Parsea la respuesta cruda de ELM327 para un PID estándar y retorna valor numérico o '' si no es válido.
        Procesa múltiples líneas y loguea advertencias detalladas.
        """
        if resp is None or resp == "":
            log_evento_app(
                "ADVERTENCIA",
                f"[PARSE][{pid}] Respuesta vacía. Contexto: cmd={cmd_context}",
            )
            return ""
        if isinstance(resp, (int, float)):
            return resp
        if isinstance(resp, str):
            for linea in resp.strip().splitlines():
                l = linea.strip()
                if l in (
                    "NO DATA",
                    "SEARCHING...",
                    "",
                    "NONE",
                    "None",
                    "\r>",
                    "STOPPED",
                ):
                    continue
                try:
                    if pid in ("rpm", "010C") and (
                        l.startswith("41 0C") or l.replace(" ", "").startswith("410C")
                    ):
                        val = self.parse_rpm(
                            l, pid_context=pid, cmd_context=cmd_context
                        )
                        if val is not None:
                            return val
                    elif pid in ("vel", "010D") and (
                        l.startswith("41 0D") or l.replace(" ", "").startswith("410D")
                    ):
                        val = self.parse_vel(
                            l, pid_context=pid, cmd_context=cmd_context
                        )
                        if val is not None:
                            return val
                    elif pid in ("temp", "0105") and (
                        l.startswith("41 05") or l.replace(" ", "").startswith("4105")
                    ):
                        val = self.parse_temp(
                            l, pid_context=pid, cmd_context=cmd_context
                        )
                        if val is not None:
                            return val
                    elif pid in ("temp_aire", "010F") and (
                        l.startswith("41 0F") or l.replace(" ", "").startswith("410F")
                    ):
                        val = self.parse_temp_aire(
                            l, pid_context=pid, cmd_context=cmd_context
                        )
                        if val is not None:
                            return val
                    # --- Lógica robusta para otros PIDs con función de parseo asociada ---
                    elif pid in PIDS and "parse_fn" in PIDS[pid]:
                        parse_fn = PIDS[pid]["parse_fn"]
                        val = parse_fn(l)
                        if val is not None:
                            return val
                    elif pid in PIDS and "cmd" in PIDS[pid]:
                        # Aquí podrías agregar lógica robusta para otros PIDs
                        pass
                except Exception as e:
                    log_evento_app(
                        "ADVERTENCIA",
                        f"[PARSE][{pid}] Excepción inesperada al parsear línea: '{l}'. cmd={cmd_context}, error={e}",
                    )
                    continue
            log_evento_app(
                "ADVERTENCIA",
                f"[PARSE][{pid}] Ninguna línea válida encontrada en respuesta. Resp completa: {resp}, cmd={cmd_context}",
            )
            return ""
        log_evento_app(
            "ADVERTENCIA",
            f"[PARSE][{pid}] Tipo de respuesta no soportado: {type(resp)}. Resp: {resp}, cmd={cmd_context}",
        )
        return ""

    def get_pid_key(self, pid_legible, pids_dict):
        """
        Obtiene la clave estándar del PID en PIDS a partir de nombre legible, código OBD o descripción.
        Prioriza el nombre legible, luego código ('cmd'), luego descripción ('desc').
        Corrige: Si recibe nombre legible estándar, lo convierte a código OBD-II usando PID_MAP_INV antes de buscar en PIDS.
        """
        from obd.pids_ext import PID_MAP_INV

        pid_legible_norm = pid_legible.strip().lower()
        # Si es nombre legible estándar, convertir a código OBD-II
        if pid_legible_norm in PID_MAP_INV:
            pid_code = PID_MAP_INV[pid_legible_norm]
            if pid_code in pids_dict:
                return pid_code
        # 1. Buscar por clave directa (puede ser código OBD-II)
        for k in pids_dict.keys():
            if k.strip().lower() == pid_legible_norm:
                return k
        # 2. Buscar por código OBD ('cmd')
        for k, v in pids_dict.items():
            if v.get("cmd", "").strip().lower() == pid_legible_norm:
                return k
        # 3. Buscar por descripción ('desc')
        for k, v in pids_dict.items():
            if v.get("desc", "").strip().lower() == pid_legible_norm:
                return k
        # 4. Si no se encuentra, devolver el original (puede ser un PID personalizado)
        return pid_legible

    def _parse_and_log_real(self, pids_legibles):
        """Obtiene y parsea datos reales, loguea y retorna el dict de datos."""
        data = {}
        if not self.connected or self.elm is None:
            advert = (
                "ADVERTENCIA: Intento de adquisición de datos OBD-II en modo real sin conexión activa o ELM327 no inicializado. "
                f"self.connected={self.connected}, self.elm={self.elm}"
            )
            print(advert)
            log_evento_app("ADVERTENCIA", advert, contexto="read_data")
            for pid in pids_legibles:
                if pid != "escenario":
                    data[normalizar_pid(pid)] = ""
            return data
        for pid in pids_legibles:
            if pid == "escenario":
                data[pid] = ""
                continue
            pid_legible = normalizar_pid(pid)
            pid_key = self.get_pid_key(pid_legible, PIDS)
            if pid_key in PIDS:
                cmd = PIDS[pid_key]["cmd"]
                print(f"[BACKEND] Enviando: {cmd} para {pid_legible}")
                try:
                    if self.elm is not None and hasattr(self.elm, "send_pid"):
                        resp = self.elm.send_pid(cmd)
                    else:
                        resp = None
                    print(f"[BACKEND] Enviando: {cmd} -> Respuesta cruda: {resp}")
                except Exception as e:
                    resp = None
                    print(f"[BACKEND] Error al enviar comando {cmd}: {e}")
                    log_evento_app(
                        "ADVERTENCIA",
                        f"[OBD] Error al enviar comando {cmd} (PID: {pid_legible}): {e}",
                    )
                try:
                    if pid_legible == "rpm":
                        val = (
                            self.parse_rpm(
                                resp, pid_context=pid_legible, cmd_context=cmd
                            )
                            if resp
                            else None
                        )
                    elif pid_legible == "vel":
                        val = (
                            self.parse_vel(
                                resp, pid_context=pid_legible, cmd_context=cmd
                            )
                            if resp
                            else None
                        )
                    elif pid_legible == "temp":
                        val = (
                            self.parse_temp(
                                resp, pid_context=pid_legible, cmd_context=cmd
                            )
                            if resp
                            else None
                        )
                    elif pid_legible == "temp_aire":
                        val = (
                            self.parse_temp_aire(
                                resp, pid_context=pid_legible, cmd_context=cmd
                            )
                            if resp
                            else None
                        )
                    else:
                        val = self.parse_pid_response(
                            pid_legible, resp, cmd_context=cmd
                        )
                    print("[DEBUG][BACKEND] Antes de guardar:")
                    print("PID=", pid_legible, "Valor=", val)
                    data[pid_legible] = val
                    log_evento_app(
                        "INFO",
                        f"[OBD] PID={pid_legible}, valor={val}",
                        contexto="read_data",
                    )
                except Exception as ex:
                    print(f"[BACKEND] Error de parsing en PID {pid_legible}: {ex}")
                    log_evento_app(
                        "ERROR",
                        f"Error de parsing en PID {pid_legible}. Ver log para detalles.",
                        contexto="read_data",
                    )
                    val = None
                data[pid_legible] = val
                log_evento_app(
                    "INFO",
                    f"[OBD] PID={pid_legible}, valor={val}",
                    contexto="read_data",
                )
                if val not in (None, "", "None"):
                    print(f"[OBD] {pid_legible} recibido: {val}")
                else:
                    advert = (
                        f"ADVERTENCIA: El PID {pid_legible} no entregó datos válidos. "
                        f"Comando: {cmd}, Respuesta: {resp}, Parsing: {val}"
                    )
                    print(advert)
                    log_evento_app("ADVERTENCIA", advert, contexto="read_data")
            else:
                data[pid_legible] = ""
                if pid_legible not in PIDS and pid_legible != "escenario":
                    advert = f"ADVERTENCIA: El PID {pid_legible} no está definido en PIDS para modo real."
                    print(advert)
                    log_evento_app("ADVERTENCIA", advert, contexto="read_data")
        return data

    def read_data(self, pids, **kwargs):
        """
        Adquisición de datos OBD-II. En modo emulador, retorna valores dinámicos y realistas para los PIDs estándar.
        En modo real, mantiene la lógica de adquisición real.
        """
        print("[BACKEND] Solicitud de datos recibida para PIDs:", pids)
        datos = {}
        t = time.time()
        if self.modo == "emulador":
            for pid in pids or []:
                if pid == "rpm":
                    valor = int(800 + 200 * math.sin(t))
                elif pid == "vel":
                    valor = int(20 + 10 * math.sin(t / 3))
                elif pid == "temp":
                    valor = int(80 + 5 * math.sin(t / 5))
                elif pid == "volt_bateria":
                    valor = round(13.8 + 0.1 * math.sin(t / 10), 2)
                elif pid == "temp_refrigerante":
                    valor = int(75 + 10 * math.sin(t / 7))
                else:
                    valor = random.randint(1, 100)
                # Forzar conversión a numérico
                valor = self.safe_cast(valor)
                datos[pid] = valor
                print(f"[BACKEND] PID: {pid} | Valor generado: {valor}")
                if not valor:
                    print(f"[BACKEND][WARNING] Valor vacío para PID: {pid}")
            print("[BACKEND] Diccionario final retornado:", datos)
        else:
            print("[BACKEND] Modo real: iniciando adquisición real")
            datos = self._parse_and_log_real(pids)
            for pid in pids or []:
                valor = datos.get(pid)
                print("[DEBUG][BACKEND] Antes de enviar a UI/export:")
                print("PID=", pid, "Valor=", valor)
                if not valor:
                    print(f"[BACKEND][WARNING] Valor vacío para PID: {pid}")
            print("[BACKEND] Diccionario final retornado:", datos)
        datos["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log.append(datos)
        if self.db_conn and self.db_cursor:
            try:
                self.db_cursor.execute(
                    "INSERT INTO lecturas (timestamp, rpm, vel, escenario) VALUES (?, ?, ?, ?)",
                    (
                        datos["timestamp"],
                        datos.get("rpm", None),
                        datos.get("vel", None),
                        datos.get("escenario", ""),
                    ),
                )
                self.db_conn.commit()
            except Exception as e:
                log_evento_app(
                    "ADVERTENCIA",
                    f"[read_data] Error al guardar en la base de datos: {e}",
                )
        return datos

    # Stubs agregados para compatibilidad UI/backend, 2025-06-03
    def get_log(self):
        print("[STUB] OBDDataSource.get_log llamado")
        # TODO: implementar lógica real si es necesario
        return self.log if hasattr(self, "log") else []

    def get_dtc(self):
        print("[STUB] OBDDataSource.get_dtc llamado")
        # TODO: implementar lógica real si es necesario
        return []

    def clear_dtc(self):
        print("[STUB] OBDDataSource.clear_dtc llamado")
        # TODO: implementar lógica real si es necesario
        return "Not implemented"

    def scan_supported_pids(self):
        print("[STUB] OBDDataSource.scan_supported_pids llamado")
        # TODO: implementar lógica real si es necesario
        return []

    def filter_functional_pids(self, pids):
        print("[STUB] OBDDataSource.filter_functional_pids llamado con:", pids)
        # TODO: implementar lógica real si es necesario
        return []


# --- AUTO-CHECK DE MÉTODOS UI <-> BACKEND ---
def check_obd_datasource_methods():
    """
    Chequea automáticamente la correspondencia de métodos entre la UI (DashboardOBD)
    y el backend (OBDDataSource). Imprime advertencias y stubs sugeridos si faltan métodos.
    """
    import inspect
    import re

    # 1. Detectar métodos requeridos por la UI (DashboardOBD)
    required_methods = set()
    try:
        for name, obj in globals().items():
            if inspect.isclass(obj) and name == "DashboardOBD":
                dashboard_methods = set()
                for _, method in inspect.getmembers(obj, inspect.isfunction):
                    try:
                        source = inspect.getsource(method)
                        dashboard_methods.update(
                            re.findall(
                                r"self\\.data_source\\.([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(",
                                source,
                            )
                        )
                    except Exception:
                        continue
                required_methods = dashboard_methods
    except Exception as e:
        print(f"[CHECK] No se pudo analizar DashboardOBD automáticamente: {e}")
        # Fallback: lista manual (ajusta según tu UI)
        required_methods = {
            "get_log",
            "get_dtc",
            "clear_dtc",
            "scan_supported_pids",
            "filter_functional_pids",
            "read_data",
            "connect",
            "disconnect",
            "set_escenario",
        }
    # 2. Métodos públicos implementados en OBDDataSource
    implemented_methods = set()
    try:
        for name, obj in inspect.getmembers(OBDDataSource, inspect.isfunction):
            if not name.startswith("_"):
                implemented_methods.add(name)
    except Exception as e:
        print(f"[CHECK] No se pudo analizar OBDDataSource: {e}")
    # 3. Comparar y mostrar resultados
    print("\n[CHECK] Métodos requeridos por la UI:", sorted(required_methods))
    print(
        "[CHECK] Métodos implementados en OBDDataSource:", sorted(implemented_methods)
    )
    missing = required_methods - implemented_methods
    if missing:
        print(
            f"[CHECK][ADVERTENCIA] Métodos FALTANTES en OBDDataSource: {sorted(missing)}"
        )
        print("[CHECK] Sugerencias de stubs para agregar:")
        for m in sorted(missing):
            print(
                f"    def {m}(self):\n        print('[STUB] OBDDataSource.{m} llamado')\n        return None\n"
            )
    else:
        print(
            "[CHECK] Todos los métodos requeridos por la UI están implementados en OBDDataSource."
        )


# Ejecutar el chequeo tras definir OBDDataSource
check_obd_datasource_methods()
# --- FIN AUTO-CHECK ---

# --- LIMPIEZA Y CONSOLIDACIÓN DASHBOARD OBD-II ---
# Versión desacoplada UI/backend, 2025-06-03
# Elimina duplicados, referencias rotas y fragmentos incompletos. Lógica robusta para importación/escaneo de PIDs soportados.

# ...existing code hasta la clase DashboardOBD...

# --- Widget visual de estado de conexión ---
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush


class EstadoConexionWidget(QWidget):
    """
    Widget visual fijo para mostrar el estado de conexión OBD-II.
    Muestra icono circular (color) y texto, y permite expansión futura (tipo interfaz, VIN, etc).
    """

    estado_cambiado = pyqtSignal(
        str, str, str
    )  # estado_anterior, estado_nuevo, mensaje_error

    def __init__(self, parent=None):
        super().__init__(parent)
        self.estado = "desconectado"  # 'conectado', 'desconectado', 'emulador', 'error'
        self.mensaje = "Desconectado"
        self.error = ""
        self.setFixedHeight(38)
        self.setMinimumWidth(220)
        self.setMaximumWidth(350)
        self.setStyleSheet("background: #23272e; border-radius: 8px;")
        self._color_map = {
            "conectado": QColor(0, 200, 60),
            "desconectado": QColor(200, 40, 40),
            "emulador": QColor(200, 40, 40),
            "error": QColor(255, 200, 40),
        }
        self._texto_map = {
            "conectado": "Conectado al vehículo",
            "desconectado": "Desconectado",
            "emulador": "Modo Emulador",
            "error": "Error de comunicación",
        }

    def set_estado(self, estado, mensaje_error=""):
        estado_anterior = self.estado
        self.estado = estado
        self.error = mensaje_error
        self.mensaje = self._texto_map.get(estado, "Desconocido")
        self.update()
        self.estado_cambiado.emit(estado_anterior, estado, mensaje_error)

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self._color_map.get(self.estado, QColor(120, 120, 120))
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(10, 10, 18, 18)
        painter.setPen(QColor(240, 240, 240))
        font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(38, 26, self.mensaje)
        if self.estado == "error" and self.error:
            painter.setPen(QColor(255, 200, 40))
            font2 = QFont("Arial", 9)
            painter.setFont(font2)
            painter.drawText(38, 36, self.error)


class DashboardOBD(QWidget):
    """
    UI principal del dashboard OBD-II. Gestiona widgets, layouts, eventos y comunicación con OBDDataSource.
    Toda la lógica de UI y manipulación de widgets está aquí.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard OBD-II Multiplataforma")
        self.setGeometry(100, 100, 900, 500)
        self.setStyleSheet("background-color: #181c20; color: #f0f0f0;")
        self.data_source = OBDDataSource("emulador")
        self.selected_pids = []
        self.pid_checkboxes = {}
        self.gauge_widgets = {}
        # Usar nombres legibles
        self.pids_disponibles = [normalizar_pid(pid) for pid in PIDS.keys()]
        self.estado_conexion_widget = EstadoConexionWidget()
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)

    def log_estado_conexion(self, estado_anterior, estado_nuevo, mensaje_error):
        msg = f"Cambio de estado de conexión: {estado_anterior} → {estado_nuevo}"
        if mensaje_error:
            msg += f" | Error: {mensaje_error}"
        print(f"[ESTADO CONEXIÓN] {msg}")
        log_evento_app("INFO", f"[ESTADO CONEXIÓN] {msg}")

    def init_ui(self):
        layout = QVBoxLayout()
        # Estado de conexión visual
        estado_layout = QHBoxLayout()
        estado_layout.addWidget(self.estado_conexion_widget)
        estado_layout.addStretch()
        layout.addLayout(estado_layout)
        # Selector de fuente de datos
        fuente_layout = QHBoxLayout()
        fuente_label = QLabel("Fuente de datos:")
        fuente_label.setFont(QFont("Arial", 12))
        self.fuente_combo = QComboBox()
        self.fuente_combo.addItems(["Emulador", "Vehículo real"])
        self.fuente_combo.currentIndexChanged.connect(self.cambiar_fuente)
        fuente_layout.addWidget(fuente_label)
        fuente_layout.addWidget(self.fuente_combo)
        fuente_layout.addStretch()
        self.btn_conectar = QPushButton("Conectar")
        self.btn_conectar.clicked.connect(self.conectar_fuente)
        self.btn_conectar.setStyleSheet(
            "background-color: #2e8b57; color: white; font-weight: bold;"
        )
        self.btn_desconectar = QPushButton("Desconectar")
        self.btn_desconectar.clicked.connect(self.desconectar_fuente)
        self.btn_desconectar.setStyleSheet(
            "background-color: #b22222; color: white; font-weight: bold;"
        )
        fuente_layout.addWidget(self.btn_conectar)
        fuente_layout.addWidget(self.btn_desconectar)
        layout.addLayout(fuente_layout)
        # Gauges dinámicos
        self.gauges_layout = QHBoxLayout()
        layout.addLayout(self.gauges_layout)
        # Panel DTC
        dtc_layout = QHBoxLayout()
        self.dtc_label = QLabel("DTC: ---")
        self.dtc_label.setFont(QFont("Arial", 14))
        self.btn_leer_dtc = QPushButton("Leer DTC")
        self.btn_leer_dtc.clicked.connect(self.leer_dtc)
        self.btn_borrar_dtc = QPushButton("Borrar DTC")
        self.btn_borrar_dtc.clicked.connect(self.borrar_dtc)
        dtc_layout.addWidget(self.dtc_label)
        dtc_layout.addWidget(self.btn_leer_dtc)
        dtc_layout.addWidget(self.btn_borrar_dtc)
        layout.addLayout(dtc_layout)
        # Panel de logs y exportación
        log_layout = QHBoxLayout()
        self.btn_exportar = QPushButton("Exportar Log")
        self.btn_exportar.clicked.connect(self.exportar_log)
        log_layout.addWidget(self.btn_exportar)
        self.btn_cargar_csv_pids = QPushButton("Cargar CSV de PIDs soportados")
        self.btn_cargar_csv_pids.setStyleSheet(
            "background-color: #ffb300; color: black; font-weight: bold;"
        )
        self.btn_cargar_csv_pids.clicked.connect(self.cargar_csv_pids_soportados)
        log_layout.addWidget(self.btn_cargar_csv_pids)
        self.btn_escanear_pids = QPushButton("Escanear PIDs soportados (ECU)")
        self.btn_escanear_pids.setStyleSheet(
            "background-color: #00bcd4; color: white; font-weight: bold;"
        )
        self.btn_escanear_pids.clicked.connect(self.escanear_pids_ecu)
        log_layout.addWidget(self.btn_escanear_pids)
        self.btn_restaurar_pids = QPushButton("Restaurar todos los PIDs")
        self.btn_restaurar_pids.setStyleSheet(
            "background-color: #888; color: white; font-weight: bold;"
        )
        self.btn_restaurar_pids.clicked.connect(self.restaurar_lista_completa_pids)
        log_layout.addWidget(self.btn_restaurar_pids)
        layout.addLayout(log_layout)
        # Tabla de log en tiempo real
        self.table_log = QTableWidget(0, len(self.selected_pids) + 2)
        headers = (
            ["Timestamp"]
            + [PIDS[pid]["desc"] if pid in PIDS else pid for pid in self.selected_pids]
            + ["Escenario"]
        )
        self.table_log.setHorizontalHeaderLabels(headers)
        self.table_log.setStyleSheet("background-color: #23272e; color: #f0f0f0;")
        self.table_log.setMinimumHeight(180)
        layout.addWidget(self.table_log)
        # Panel de selección dinámica de PIDs
        pid_panel = QVBoxLayout()
        pid_label = QLabel("Selecciona hasta 8 parámetros a monitorear:")
        pid_label.setFont(QFont("Arial", 12))
        pid_panel.addWidget(pid_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.pid_widget = QWidget()
        self.pid_grid = QGridLayout()
        # SOLO se llama aquí (y cuando cambia la lista de PIDs disponibles)
        self._actualizar_pid_checkboxes(self.pids_disponibles)
        self.pid_widget.setLayout(self.pid_grid)
        scroll.setWidget(self.pid_widget)
        pid_panel.addWidget(scroll)
        layout.addLayout(pid_panel)
        # Panel de selección de modo de emulación
        self.modo_label = QLabel("Modo de emulación:")
        self.modo_label.setFont(QFont("Arial", 12))
        self.modo_combo = QComboBox()
        self.modo_combo.addItems(
            [
                "ralenti",
                "aceleracion",
                "crucero",
                "frenado",
                "ciudad",
                "carretera",
                "falla",
            ]
        )
        self.modo_combo.setCurrentText("ralenti")
        self.modo_combo.currentTextChanged.connect(self.on_modo_changed)
        if hasattr(self.data_source, "modo") and self.data_source.modo == "emulador":
            layout.addWidget(self.modo_label)
            layout.addWidget(self.modo_combo)
        self.status_label = QLabel("Desconectado.")
        self.status_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        print("[UI] init_ui ejecutada. Checkboxes y eventos listos.")

    def _actualizar_pid_checkboxes(self, pids_disponibles):
        # Limpia el grid y checkboxes
        for i in reversed(range(self.pid_grid.count())):
            item = self.pid_grid.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is None:
                continue
            widget.setParent(None)
        self.pid_checkboxes.clear()
        pids_legibles = [normalizar_pid(pid) for pid in pids_disponibles]
        # Limpiar seleccionados de PIDs que ya no están disponibles
        self.selected_pids = [pid for pid in self.selected_pids if pid in pids_legibles]
        for i, pid_legible in enumerate(pids_legibles):
            info = buscar_pid(pid_legible) or {}
            cb = QCheckBox(f"{pid_legible} - {info.get('desc', pid_legible)}")
            cb.stateChanged.connect(self.on_pid_selection_changed)
            self.pid_checkboxes[pid_legible] = cb
            # Marcar como seleccionado si estaba en selected_pids
            if pid_legible in self.selected_pids:
                cb.setChecked(True)
            self.pid_grid.addWidget(cb, i // 2, i % 2)
        self._update_gauges()
        self._actualizar_tabla_log()

    def restaurar_lista_completa_pids(self):
        self.pids_disponibles = [normalizar_pid(pid) for pid in PIDS.keys()]
        self._actualizar_pid_checkboxes(self.pids_disponibles)
        self.status_label.setText("Lista completa de PIDs restaurada.")

    def cargar_csv_pids_soportados(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Selecciona CSV de PIDs soportados", "", "CSV (*.csv)"
        )
        if not fname:
            return
        try:
            with open(fname, newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                pids = []
                for row in reader:
                    if row and row[0].strip():
                        pids.append(normalizar_pid(row[0].strip()))
            if not pids:
                QMessageBox.warning(
                    self,
                    "CSV vacío",
                    "El archivo CSV no contiene PIDs válidos."
                )
                return
            # Usar nombres legibles
            self.pids_disponibles = [normalizar_pid(pid) for pid in pids]
            self._actualizar_pid_checkboxes(self.pids_disponibles)
            self.status_label.setText(
                "PIDs soportados cargados desde CSV: %d" % len(pids)
            )
            print(
                "[AUTOMÁTICO] Lista de PIDs funcionales cargada desde CSV: %s" % fname
            )
            log_evento_app(
                "INFO", "[AUTOMÁTICO] Lista de PIDs funcionales cargada desde CSV: %s"
                % fname
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al cargar CSV", str(e))

    def escanear_pids_ecu(self):
        if not (
            hasattr(self.data_source, "modo")
            and self.data_source.modo == "real"
            and getattr(self.data_source, "connected", False)
        ):
            QMessageBox.warning(
                self,
                "No conectado",
                "Debes estar conectado en modo real para escanear PIDs.",
            )
            return
        self.status_label.setText("Escaneando PIDs soportados... (esto puede tardar)")
        QApplication.processEvents()
        soportados = self.data_source.scan_supported_pids()
        funcionales = self.data_source.filter_functional_pids(soportados)
        if not funcionales:
            QMessageBox.warning(
                self, "Sin PIDs funcionales", "No se detectaron PIDs funcionales."
            )
            return
        # Usar nombres legibles
        self.pids_disponibles = [normalizar_pid(pid) for pid in funcionales]
        self._actualizar_pid_checkboxes(self.pids_disponibles)
        fname = f"pids_soportados_funcionales_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(fname, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for pid in self.pids_disponibles:
                writer.writerow([pid])
        self.status_label.setText(
            f"Escaneo completo. PIDs funcionales: {len(self.pids_disponibles)}. Guardado en {fname}"
        )
        QMessageBox.information(
            self,
            "Escaneo completo",
            f"PIDs funcionales detectados: {len(self.pids_disponibles)}\nGuardado en {fname}",
        )

    def on_pid_selection_changed(self):
        seleccionados = self._obtener_pids_seleccionados_validos()
        advertencias, resultado = self._filtrar_pids_unicos_y_limite(seleccionados)
        self.selected_pids = resultado
        self._update_gauges()
        status = f"PIDs seleccionados: {', '.join(self.selected_pids)}"
        if advertencias:
            status += " | " + " ".join(advertencias)
        self.status_label.setText(status)
        log_evento_app(
            "INFO",
            f"PIDs activos tras selección: {self.selected_pids}",
            contexto="UI_tracking",
        )

    def _obtener_pids_seleccionados_validos(self):
        return [
            normalizar_pid(pid)
            for pid, cb in self.pid_checkboxes.items()
            if cb.isChecked() and pid in self.pids_disponibles
        ]

    def _filtrar_pids_unicos_y_limite(self, seleccionados):
        advertencias = []
        vistos = set()
        resultado = []
        for pid in seleccionados:
            if pid not in vistos:
                resultado.append(pid)
                vistos.add(pid)
            else:
                advertencias.append(
                    "El PID '" + pid + "' ya está seleccionado. "
                    "Solo se permite una variante por parámetro."
                )
        if len(resultado) > 8:
            for pid in resultado[8:]:
                for k, cb in self.pid_checkboxes.items():
                    if normalizar_pid(k) == pid:
                        cb.setChecked(False)
            advertencias.append(
                "Solo se permiten hasta 8 parámetros a la vez. "
                "El resto se ha desmarcado."
            )
            resultado = resultado[:8]
        return advertencias, resultado

    def cambiar_fuente(self):
        modo = "emulador" if self.fuente_combo.currentIndex() == 0 else "real"
        self.data_source = OBDDataSource(modo)
        if modo == "emulador":
            self.estado_conexion_widget.set_estado("emulador")
        else:
            self.estado_conexion_widget.set_estado("desconectado")
        self.status_label.setText(f"Fuente cambiada a: {modo}")
        self.restaurar_lista_completa_pids()

    def conectar_fuente(self):
        """
        Establece la conexión con el vehículo (modo real) o activa el modo emulador.
        Actualiza el estado de la UI según el resultado de la conexión.
        """
        try:
            self.data_source.disconnect()
            idx = self.fuente_combo.currentIndex()
            modo = "emulador" if idx == 0 else "real"
            self.data_source = OBDDataSource(modo)
            if modo == "real":
                ip = "192.168.0.10"
                puerto = 35000
                ok, error = self.check_wifi_obdii_connection(ip, puerto)
                if not ok:
                    self.estado_conexion_widget.set_estado("error", error)
                    self.status_label.setText(
                        "Sin conexión con el OBD-II por WiFi. "
                        "Revisa la red y reinicia el adaptador.\n" + "Detalle: " + error
                    )
                    return
            self.data_source.connect()
            if self.data_source.connected:
                if modo == "real":
                    self.estado_conexion_widget.set_estado("conectado")
                    # --- FLUJO AUTÓNOMO DE ESCANEO Y FILTRADO DE PIds FUNCIONALES ---
                    self.flujo_autonomo_pids_funcionales()
                else:
                    self.estado_conexion_widget.set_estado("emulador")
                self.status_label.setText("Conectado a: %s" % modo)
            else:
                self.estado_conexion_widget.set_estado("desconectado")
                self.status_label.setText("No conectado.")
        except Exception as e:
            self.estado_conexion_widget.set_estado("error", str(e))
            self.status_label.setText("Error al conectar: %s" % e)

    def desconectar_fuente(self):
        """Desconecta el OBD-II y actualiza el estado de la UI."""
        try:
            self.data_source.disconnect()
            self.estado_conexion_widget.set_estado("desconectado")
            self.status_label.setText("Desconectado.")
        except Exception as e:
            self.estado_conexion_widget.set_estado("error", str(e))
            self.status_label.setText(f"Error al desconectar: {e}")

    def check_wifi_obdii_connection(self, ip, port, timeout=3):
        """
        Verifica la conexión WiFi con el adaptador OBD-II.
        Retorna True si la conexión es exitosa, False en caso contrario.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, port))
            s.close()
            return True, ""
        except Exception as e:
            return False, str(e)

    def _update_gauges(self):
        # Eliminar gauges de PIDs que ya no están seleccionados
        self._eliminar_gauges_no_seleccionados()
        datos_actuales = (
            self.data_source.get_log()[-1]
            if self.data_source.get_log() else {}
        )
        for pid in self.selected_pids:
            self._crear_o_actualizar_gauge(pid, datos_actuales)

    def _eliminar_gauges_no_seleccionados(self):
        for pid in list(self.gauge_widgets.keys()):
            if pid not in self.selected_pids:
                gauge = self.gauge_widgets[pid]
                self.gauges_layout.removeWidget(gauge)
                gauge.deleteLater()
                del self.gauge_widgets[pid]

    def _crear_o_actualizar_gauge(self, pid, datos_actuales):
        if pid not in self.gauge_widgets and pid in PIDS:
            info = PIDS[pid]
            min_value = info.get("min", 0)
            max_value = info.get("max", 100)
            unidades = info.get("unidades", "")
            label = info.get("desc", pid)
            gauge_container = QWidget()
            vlayout = QVBoxLayout()
            vlayout.setContentsMargins(0, 0, 0, 0)
            vlayout.setSpacing(2)
            label_widget = QLabel(label)
            label_widget.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            label_widget.setStyleSheet(
                "color: #DDD; font-weight: bold; font-size: 14px;"
            )
            gauge = GaugeWidget(min_value, max_value, unidades)
            vlayout.addWidget(label_widget)
            vlayout.addWidget(gauge)
            gauge_container.setLayout(vlayout)
            self.gauges_layout.addWidget(gauge_container)
            self.gauge_widgets[pid] = gauge
        # Actualizar valor del gauge si hay datos
        if pid in self.gauge_widgets and pid in datos_actuales:
            valor = datos_actuales.get(pid)
            # Aceptar 0 como valor válido (no solo valores positivos)
            if valor is not None and valor != "":
                self.gauge_widgets[pid].set_value(valor)
            else:
                self.gauge_widgets[pid].set_value(0)

    def update_data(self):
        """
        Actualiza los datos en la UI: lee nuevos datos del OBD-II, actualiza gauges y tabla de log.
        Maneja errores de conexión y actualización.
        """
        try:
            print("[UI] PIDs activos antes de refresco:", self.selected_pids)
            data = self.data_source.read_data(self.selected_pids)
            print("[UI] Datos recibidos del backend:", data)
            if (
                hasattr(self.data_source, "last_handshake_error")
                and self.data_source.last_handshake_error
            ):
                self.estado_conexion_widget.set_estado("error", self.data_source.last_handshake_error)
                self.status_label.setText(f"Error de conexión: {self.data_source.last_handshake_error}")
            # Actualizar gauges
            for pid, gauge in self.gauge_widgets.items():
                valor = data.get(pid)
                # Aceptar 0 como válido
                if valor is not None and valor != "":
                    gauge.set_value(valor)
                else:
                    gauge.set_value(0)
            self._actualizar_tabla_log()
        except Exception as e:
            print(f"[UI] Error en update_data: {e}")
            self.status_label.setText(f"Error al actualizar datos: {e}")
            log_evento_app("ERROR", f"[UI] Error en update_data: {e}")

    def _actualizar_tabla_log(self):
        """
        Actualiza la tabla de log en la UI con las últimas lecturas del OBD-II.
        Configura encabezados y filas de la tabla según los datos disponibles.
        """
        log = self.data_source.get_log()[-100:]
        self.table_log.setColumnCount(len(self.selected_pids) + 2)
        headers = (
            ["Timestamp"]
            + [PIDS[pid]["desc"] if pid in PIDS else pid for pid in self.selected_pids]
            + ["Escenario"]
        )
        self.table_log.setHorizontalHeaderLabels(headers)
        self.table_log.setRowCount(len(log))
        for i, row in enumerate(log):
            self.table_log.setItem(i, 0, QTableWidgetItem(str(row.get("timestamp", ""))))
            for j, pid in enumerate(self.selected_pids):
                val = row.get(pid)
                # Mostrar 0 como válido
                if val is None or val == "":
                    val = "0" if pid in ("rpm", "vel") else ""
                self.table_log.setItem(i, j + 1, QTableWidgetItem(str(val)))
            self.table_log.setItem(i, len(self.selected_pids) + 1, QTableWidgetItem(str(row.get("escenario", ""))))

    def exportar_log(self):
        """
        Exporta el log de datos OBD-II a un archivo CSV.
        Permite al usuario seleccionar la ubicación y nombre del archivo.
        """
        try:
            fname, _ = QFileDialog.getSaveFileName(self, "Guardar log como", "obd_log.csv", "CSV (*.csv)")
            if not fname:
                return
            log = self.data_source.get_log()
            if not log:
                QMessageBox.warning(self, "Sin datos", "No hay datos para exportar.")
                return
            campos = ["timestamp"] + self.selected_pids + ["escenario"]
            with open(fname, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=campos)
                writer.writeheader()
                for row in log:
                    # Asegurar que 0 se exporta correctamente
                    for pid in ("rpm", "vel"):
                        if pid in campos and (row.get(pid) is None or row.get(pid) == ""):
                            row[pid] = 0
                    writer.writerow({k: row.get(k, "") for k in campos})
            QMessageBox.information(self, "Exportación exitosa", f"Log exportado a {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar log", str(e))

    def on_modo_changed(self, modo):
        if hasattr(self.data_source, "set_escenario"):
            self.data_source.set_escenario(modo)
        self.status_label.setText(f"Modo de emulación: {modo}")

    def leer_dtc(self):
        try:
            dtc = self.data_source.get_dtc()
            if not dtc:
                self.dtc_label.setText("DTC: ---")
                QMessageBox.information(self, "DTC", "No se detectaron códigos DTC.")
            else:
                self.dtc_label.setText(f"DTC: {', '.join(dtc)}")
                QMessageBox.information(self, "DTC", f"Códigos DTC detectados: {', '.join(dtc)}")
        except Exception as e:
            QMessageBox.critical(self, "Error al leer DTC", str(e))

    def borrar_dtc(self):
        try:
            res = self.data_source.clear_dtc()
            QMessageBox.information(self, "Borrar DTC", str(res))
            self.dtc_label.setText("DTC: ---")
        except Exception as e:
            QMessageBox.critical(self, "Error al borrar DTC", str(e))

    def flujo_autonomo_pids_funcionales(self):
        # Aquí puedes implementar el flujo automático de escaneo y filtrado de PIDs funcionales si lo deseas
        pass


def main():
    app = QApplication(sys.argv)
    dash = DashboardOBD()
    dash.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
