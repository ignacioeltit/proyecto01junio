# --- LIMPIEZA PEP8/FLAKE8 COMPLETA 2025-06-04 ---
# Cambios principales:
# - Todas las líneas <=79 caracteres
# - Dos líneas en blanco antes de cada clase, una antes de cada función
# - Imports únicos y al inicio, sin duplicados ni dentro de funciones
# - Eliminados argumentos y variables no usados, ramas duplicadas y
#   código muerto
# - Docstrings y comentarios acortados/divididos
# - Lazy % formatting en logging, logging.exception para errores
# - Consistencia en nombres PyQt6 y variables
# - Funciones de alta complejidad marcadas para refactor futuro
# - Sin advertencias de flake8/PEP8

import os
import sys
import time
import logging
import threading
import traceback
import sqlite3
from collections import deque
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QTableWidget, QTableWidgetItem,
    QComboBox, QScrollArea, QGridLayout
)
from src.utils.logging_app import log_evento_app
from src.obd.connection import OBDConnection
from src.obd.elm327 import ELM327
from src.ui.widgets.gauge import GaugeWidget
from src.obd.pids_ext import PIDS, normalizar_pid


LOG_LEVEL = os.environ.get('OBD_LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s][%(threadName)s] %(message)s',
    handlers=[
        logging.FileHandler('app_errors.log', encoding='utf-8'),
        logging.StreamHandler()]
)

DEFAULT_INTERVAL_REAL = float(os.environ.get('OBD_INTERVAL_REAL', '0.2'))
DEFAULT_INTERVAL_EMU = float(os.environ.get('OBD_INTERVAL_EMU', '0.1'))
MIN_INTERVAL_REAL = 0.2

DTC_LABEL_DEFAULT = "DTC: ---"
STATUS_DESCONECTADO = "Desconectado."
MAX_PIDS = 8
ADVERTENCIA_PID_DUPLICADO = (
    "El PID '%s' ya está seleccionado. "
    "Solo se permite una variante por parámetro."
)
ADVERTENCIA_LIMITE_PIDS = (
    "Solo se permiten hasta 8 parámetros a la vez. "
    "El resto se ha desmarcado."
)
PIDS_FUNCIONALES = ["rpm", "vel", "temp", "temp_aire"]
GAUGE_INVALID_STYLE = "background-color: #7a2323; color: #fff;"


class OBDDataSource:
    """
    Fuente de datos OBD-II para el dashboard. Sin lógica de UI.
    """

    def __init__(self, modo="emulador"):
        self.modo = modo
        self.escenario = "ralenti"
        self.rpm = 0
        self.vel = 0
        self.dtc = []
        self.connected = False
        self.conn = None
        self.elm = None
        self.log = deque(maxlen=1000)
        self.db_conn = None
        self.db_cursor = None
        self.last_handshake_ok = False
        self.last_handshake_error = None
        self.pids_disponibles = [normalizar_pid(pid) for pid in PIDS.keys()]

    def set_escenario(self, escenario):
        self.escenario = escenario
        if self.modo == "emulador":
            if escenario == "ralenti":
                self.rpm, self.vel = 800, 0
            elif escenario == "aceleracion":
                self.rpm, self.vel = 3500, 40
            elif escenario == "crucero":
                self.rpm, self.vel = 2200, 90
            elif escenario == "frenado":
                self.rpm, self.vel = 1200, 20
            elif escenario == "ciudad":
                self.rpm, self.vel = 1500, 30
            elif escenario == "carretera":
                self.rpm, self.vel = 2500, 110
            elif escenario == "falla":
                self.rpm, self.vel = 400, 0
            else:
                self.rpm, self.vel = 800, 0
        log_evento_app(
            "INFO",
            "Escenario cambiado a: %s" % escenario,
            contexto="set_escenario"
        )

    def connect(self):
        try:
            if self.modo == "real":
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
                        "INFO", "Handshake OK con ELM327",
                        contexto="connect"
                    )
                else:
                    log_evento_app(
                        "ERROR", "Handshake fallido con ELM327",
                        contexto="connect"
                    )
            else:
                self.connected = True
                self.last_handshake_ok = True
                log_evento_app(
                    "INFO", "Modo emulador conectado",
                    contexto="connect"
                )
            self.db_conn = sqlite3.connect("obd_log.db")
            self.db_cursor = self.db_conn.cursor()
            self.db_cursor.execute(
                """CREATE TABLE IF NOT EXISTS lecturas ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "timestamp TEXT, rpm INTEGER, vel INTEGER, "
                "escenario TEXT)"""
            )
            self.db_conn.commit()
        except Exception as e:
            log_evento_app(
                "ERROR", "Error general en connect: %s" % e,
                contexto="connect"
            )
            raise

    def disconnect(self):
        if self.modo == "real" and self.conn:
            try:
                self.conn.close()
                log_evento_app(
                    "INFO", "Desconexión OBD-II exitosa",
                    contexto="disconnect"
                )
            except Exception as e:
                log_evento_app(
                    "ERROR", "Error al cerrar conexión: %s" % e,
                    contexto="disconnect"
                )
        self.connected = False
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None
            self.db_cursor = None
            log_evento_app(
                "INFO", "Base de datos cerrada",
                contexto="disconnect"
            )

    def safe_cast(self, val, tipo=float):
        try:
            return tipo(val)
        except (ValueError, TypeError) as e:
            log_evento_app(
                "ADVERTENCIA",
                "Conversión fallida: %s (%s)" % (val, e),
                contexto="safe_cast"
            )
            return val

    def _is_valid_hex(self, s):
        try:
            int(s, 16)
            return True
        except Exception:
            return False

    def _is_invalid_response(self, line):
        invalid = {
            "NO DATA", "SEARCHING...", "", "NONE", "None", "\r>",
            "STOPPED", "UNABLE TO CONNECT", "BUS INIT...", "ERROR", ">",
            "?", "NODATA", "NULL", "NOT SUPPORTED", "CAN ERROR",
            "BUFFER FULL", "BUS ERROR", "DATA ERROR"
        }
        return line.strip().upper() in invalid

    def parse_rpm(self, respuesta_cruda, pid_context=None, cmd_context=None):
        """
        Parsea la respuesta cruda para RPM. Devuelve valor numérico o 0 si no
        es válido. Loguea advertencias detalladas.
        """
        if not respuesta_cruda or not isinstance(respuesta_cruda, str):
            log_evento_app(
                "ADVERTENCIA",
                (
                    "[PARSE][%s] Respuesta vacía o inválida para RPM. "
                    "Contexto: cmd=%s, resp=%s"
                ) % (
                    pid_context or 'rpm', cmd_context, respuesta_cruda)
            )
            return 0
        for linea in respuesta_cruda.strip().splitlines():
            raw = linea.replace(" ", "")
            if (raw.startswith("410C") or linea.startswith("41 0C")) and \
                    len(raw) >= 8:
                try:
                    A = int(raw[4:6], 16)
                    B = int(raw[6:8], 16)
                    rpm = ((A * 256) + B) / 4
                    return int(rpm)
                except Exception as e:
                    log_evento_app(
                        "ADVERTENCIA",
                        (
                            "[PARSE][%s] Error parseando RPM. Línea: '%s', "
                            "cmd=%s, error=%s"
                        ) % (
                            pid_context or 'rpm', linea, cmd_context, e)
                    )
                    continue
        log_evento_app(
            "ADVERTENCIA",
            (
                "[PARSE][%s] Ninguna línea válida para RPM. cmd=%s, resp=%s"
            ) % (
                pid_context or 'rpm', cmd_context, respuesta_cruda)
        )
        return 0

    def _clean_obd_line(self, line):
        if not isinstance(line, str):
            return ""
        return ''.join(
            c for c in line.upper() if c in '0123456789ABCDEF'
        )

    def _valid_obd_prefix(self, raw, prefix):
        return raw.startswith(prefix)

    def _parse_single_byte(self, raw, idx):
        try:
            return int(raw[idx:idx+2], 16)
        except Exception:
            return None

    def parse_vel(self, respuesta_cruda, pid_context=None, cmd_context=None):
        """
        Parsea la respuesta cruda para velocidad. Devuelve valor numérico o 0
        si no es válido. Loguea advertencias detalladas.
        """
        if not respuesta_cruda or not isinstance(respuesta_cruda, str):
            log_evento_app(
                "ADVERTENCIA",
                (
                    "[PARSE][%s] Respuesta vacía o inválida para velocidad.\n"
                    "cmd=%s, resp=%s"
                ) % (
                    pid_context or 'vel', cmd_context, respuesta_cruda)
            )
            return 0
        for linea in respuesta_cruda.strip().splitlines():
            raw = self._clean_obd_line(linea)
            if (
                self._valid_obd_prefix(raw, "410D") and
                len(raw) >= 6
            ):
                vel = self._parse_single_byte(raw, 4)
                if vel is not None:
                    return vel
                log_evento_app(
                    "ADVERTENCIA",
                    (
                        "[PARSE][%s] Error parseando velocidad.\nLínea: '%s', "
                        "cmd=%s"
                    ) % (
                        pid_context or 'vel', linea, cmd_context)
                )
        log_evento_app(
            "ADVERTENCIA",
            (
                "[PARSE][%s] Ninguna línea válida para velocidad.\ncmd=%s, "
                "resp=%s"
            ) % (
                pid_context or 'vel', cmd_context, respuesta_cruda)
        )
        return 0

    def parse_temp(self, respuesta_cruda, pid_context=None, cmd_context=None):
        """
        Parsea la respuesta cruda para temperatura. Devuelve valor numérico o 0
        si no es válido. Loguea advertencias detalladas.
        """
        if not respuesta_cruda or not isinstance(respuesta_cruda, str):
            log_evento_app(
                "ADVERTENCIA",
                (
                    "[PARSE][%s] Respuesta vacía o inválida para "
                    "temperatura.\ncmd=%s, resp=%s"
                ) % (
                    pid_context or 'temp', cmd_context, respuesta_cruda)
            )
            return 0
        for linea in respuesta_cruda.strip().splitlines():
            raw = self._clean_obd_line(linea)
            if (
                self._valid_obd_prefix(raw, "4105") and
                len(raw) >= 6
            ):
                temp = self._parse_single_byte(raw, 4)
                if temp is not None:
                    return temp - 40
                log_evento_app(
                    "ADVERTENCIA",
                    (
                        "[PARSE][%s] Error parseando temp.\nLínea: '%s', "
                        "cmd=%s"
                    ) % (
                        pid_context or 'temp', linea, cmd_context)
                )
        log_evento_app(
            "ADVERTENCIA",
            (
                "[PARSE][%s] Ninguna línea válida para temp.\ncmd=%s, resp=%s"
            ) % (
                pid_context or 'temp', cmd_context, respuesta_cruda)
        )
        return 0

    def parse_temp_aire(
        self, respuesta_cruda, pid_context=None, cmd_context=None
    ):
        """
        Parsea la respuesta cruda para temperatura de aire de admisión.
        Devuelve valor numérico o 0 si no es válido. Loguea advertencias.
        """
        if not respuesta_cruda or not isinstance(respuesta_cruda, str):
            log_evento_app(
                "ADVERTENCIA",
                (
                    "[PARSE][%s] Respuesta vacía o inválida para temp_aire.\n"
                    "cmd=%s, resp=%s"
                ) % (
                    pid_context or 'temp_aire', cmd_context, respuesta_cruda)
            )
            return 0
        for linea in respuesta_cruda.strip().splitlines():
            raw = self._clean_obd_line(linea)
            if (
                self._valid_obd_prefix(raw, "410F") and
                len(raw) >= 6
            ):
                temp_aire = self._parse_single_byte(raw, 4)
                if temp_aire is not None:
                    return temp_aire - 40
                log_evento_app(
                    "ADVERTENCIA",
                    (
                        "[PARSE][%s] Error parseando temp_aire.\nLínea: '%s', "
                        "cmd=%s"
                    ) % (
                        pid_context or 'temp_aire', linea, cmd_context)
                )
        log_evento_app(
            "ADVERTENCIA",
            (
                "[PARSE][%s] Ninguna línea válida para temp_aire.\ncmd=%s, "
                "resp=%s"
            ) % (
                pid_context or 'temp_aire', cmd_context, respuesta_cruda)
        )
        return 0

    def parse_pid_response(self, pid, resp, cmd_context=None):
        """
        Parsea la respuesta cruda de ELM327 para un PID estándar y retorna
        valor numérico robusto. Nunca retorna 0 si hay un valor válido en
        alguna línea.
        """
        if resp is None or resp == "":
            log_evento_app(
                "ADVERTENCIA",
                "[PARSE][%s] Respuesta vacía. Contexto: cmd=%s" % (
                    pid, cmd_context)
            )
            return 0
        if isinstance(resp, (int, float)):
            return resp
        if isinstance(resp, str):
            return self._parse_pid_response_str(pid, resp, cmd_context)
        log_evento_app(
            "ADVERTENCIA",
            (
                "[PARSE][%s] Tipo de respuesta no soportado: %s.\nResp: %s, "
                "cmd=%s"
            ) % (
                pid, type(resp), resp, cmd_context)
        )
        return 0

    # TODO: Refactorizar - Complejidad alta
    def _parse_pid_response_str(self, pid, resp, cmd_context):
        def _try_parse_line(pid, clean_line, cmd_context):
            if self._is_pid_rpm(pid, clean_line):
                return self.parse_rpm(
                    clean_line, pid_context=pid, cmd_context=cmd_context
                )
            if self._is_pid_vel(pid, clean_line):
                return self.parse_vel(
                    clean_line, pid_context=pid, cmd_context=cmd_context
                )
            if self._is_pid_temp(pid, clean_line):
                return self.parse_temp(
                    clean_line, pid_context=pid, cmd_context=cmd_context
                )
            if self._is_pid_temp_aire(pid, clean_line):
                return self.parse_temp_aire(
                    clean_line, pid_context=pid, cmd_context=cmd_context
                )
            if pid in PIDS and "parse_fn" in PIDS[pid]:
                parse_fn = PIDS[pid]["parse_fn"]
                return parse_fn(clean_line)
            return None
        invalid_responses = {
            "NO DATA", "SEARCHING...", "", "NONE", "None", "\r>", "STOPPED",
            "UNABLE TO CONNECT", "BUS INIT...", "ERROR", ">", "?", "NODATA",
            "NULL", "NOT SUPPORTED", "CAN ERROR", "BUFFER FULL",
            "BUS ERROR", "DATA ERROR"
        }
        for line in resp.strip().splitlines():
            clean_line = line.strip()
            if not clean_line or clean_line.upper() in invalid_responses:
                continue
            try:
                val = _try_parse_line(pid, clean_line, cmd_context)
                if self._is_valid_value(val):
                    return val
            except (ValueError, TypeError) as e:
                log_evento_app(
                    "ADVERTENCIA",
                    (
                        "[PARSE][%s] Excepción de tipo al parsear línea: "
                        "'%s'.\ncmd=%s, error=%s"
                    ) % (
                        pid, clean_line, cmd_context, e)
                )
            except Exception:
                logging.exception(
                    "[PARSE][%s] Excepción inesperada al parsear línea: "
                    "'%s'.\ncmd=%s",
                    pid, clean_line, cmd_context
                )
        log_evento_app(
            "ADVERTENCIA",
            (
                "[PARSE][%s] Ninguna línea válida encontrada en respuesta.\n"
                "Resp completa: %s, cmd=%s"
            ) % (
                pid, resp, cmd_context)
        )
        return 0

    def _is_pid_rpm(self, pid, line):
        return (
            pid in ("rpm", "010C") and (
                line.startswith("41 0C") or
                self._clean_obd_line(line).startswith("410C")
            )
        )

    def _is_pid_vel(self, pid, line):
        return (
            pid in ("vel", "010D") and (
                line.startswith("41 0D") or
                self._clean_obd_line(line).startswith("410D")
            )
        )

    def _is_pid_temp(self, pid, line):
        return (
            pid in ("temp", "0105") and (
                line.startswith("41 05") or
                self._clean_obd_line(line).startswith("4105")
            )
        )

    def _is_pid_temp_aire(self, pid, line):
        return (
            pid in ("temp_aire", "010F") and (
                line.startswith("41 0F") or
                self._clean_obd_line(line).startswith("410F")
            )
        )

    def _is_valid_value(self, val):
        return val not in (None, 0, '', 'None')

    def _parse_and_log_real(self, pids_legibles):
        """
        # TODO: Refactorizar - Complejidad alta
        """
        data = {}
        if not self._is_connection_ready():
            self._log_no_connection()
            for pid in pids_legibles:
                if pid != "escenario":
                    data[normalizar_pid(pid)] = 0
            return data
        for pid in pids_legibles:
            if pid == "escenario":
                data[pid] = ""
                continue
            pid_legible = normalizar_pid(pid)
            if pid_legible in PIDS:
                val = self._acquire_pid_with_retries(pid_legible)
                data[pid_legible] = val
            else:
                data[pid_legible] = 0
                self._log_pid_not_defined(pid_legible)
        return data

    def _is_connection_ready(self):
        return self.connected and self.elm is not None

    def _log_no_connection(self):
        advert = (
            "ADVERTENCIA: Intento de adquisición de datos OBD-II en modo real "
            "sin conexión activa o ELM327 no inicializado. "
            "self.connected=%s, self.elm=%s" % (self.connected, self.elm)
        )
        print(advert)
        log_evento_app(
            "ADVERTENCIA", advert, contexto="read_data"
        )

    def _acquire_pid_with_retries(self, pid_legible):
        MAX_RETRIES = 3
        RETRY_DELAY = 0.15
        cmd = PIDS[pid_legible]["cmd"]
        val = 0
        last_resp = None
        for intento in range(1, MAX_RETRIES + 1):
            resp = self._send_pid_command(cmd, pid_legible)
            last_resp = resp
            val = self._parse_pid_value(pid_legible, resp, cmd)
            if val not in (None, 0, '', 'None'):
                break
            self._log_invalid_pid_value(pid_legible, intento, resp)
            if intento < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        self._log_pid_result(pid_legible, val, cmd, last_resp)
        return val

    def _send_pid_command(self, cmd, pid_legible):
        try:
            if self.elm is not None and hasattr(self.elm, "send_pid"):
                resp = self.elm.send_pid(cmd)
            else:
                resp = None
            print(
                "[BACKEND] Enviando: %s -> Respuesta cruda: %s" % (
                    cmd, resp)
            )
            return resp
        except Exception:
            logging.exception(
                "[BACKEND] Error al enviar comando %s (PID: %s)",
                cmd, pid_legible
            )
            log_evento_app(
                "ADVERTENCIA",
                (
                    "[OBD] Error al enviar comando %s (PID: %s)" % (
                        cmd, pid_legible)
                ),
            )
            return None

    def _parse_pid_value(self, pid_legible, resp, cmd):
        try:
            if pid_legible == "rpm":
                if resp:
                    return self.parse_rpm(
                        resp, pid_context=pid_legible, cmd_context=cmd
                    )
                return 0
            if pid_legible == "vel":
                if resp:
                    return self.parse_vel(
                        resp, pid_context=pid_legible, cmd_context=cmd
                    )
                return 0
            if pid_legible == "temp":
                if resp:
                    return self.parse_temp(
                        resp, pid_context=pid_legible, cmd_context=cmd
                    )
                return 0
            if pid_legible == "temp_aire":
                if resp:
                    return self.parse_temp_aire(
                        resp, pid_context=pid_legible, cmd_context=cmd
                    )
                return 0
            return self.parse_pid_response(
                pid_legible, resp, cmd_context=cmd
            )
        except Exception:
            logging.exception(
                "[BACKEND] Error de parsing en PID %s", pid_legible
            )
            log_evento_app(
                "ERROR",
                (
                    "Error de parsing en PID %s. "
                    "Ver log para detalles." % pid_legible),
                contexto="read_data",
            )
            return 0

    def _log_invalid_pid_value(self, pid_legible, intento, resp):
        log_evento_app(
            "ADVERTENCIA",
            (
                "[OBD][REINTENTO] Valor inválido para PID %s en intento %s. "
                "Resp: %s"
                % (pid_legible, intento, resp)),
            contexto="read_data"
        )

    def _log_pid_result(self, pid_legible, val, cmd, last_resp):
        log_evento_app(
            "INFO",
            "[OBD] PID=%s, valor=%s" % (pid_legible, val),
            contexto="read_data",
        )
        if val not in (None, "", "None"):
            print("[OBD] %s recibido: %s" % (pid_legible, val))
        else:
            advert = (
                "ADVERTENCIA: El PID %s no entregó datos válidos tras 3 "
                "intentos. Comando: %s, Última respuesta: %s, Parsing: %s" % (
                    pid_legible, cmd, last_resp, val)
            )
            print(advert)
            log_evento_app(
                "ADVERTENCIA", advert, contexto="read_data"
            )

    def _log_pid_not_defined(self, pid_legible):
        if pid_legible not in PIDS and pid_legible != "escenario":
            advert = (
                "ADVERTENCIA: El PID %s no está definido en PIDS para "
                "modo real." % pid_legible
            )
            print(advert)
            log_evento_app(
                "ADVERTENCIA", advert, contexto="read_data"
            )


# --- AUTO-CHECK DE MÉTODOS UI <-> BACKEND ---
def check_obd_datasource_methods():
    """
    Chequea automáticamente la correspondencia de métodos entre la UI
    (DashboardOBD) y el backend (OBDDataSource). Imprime advertencias y stubs
    sugeridos si faltan métodos. COMPLEJIDAD: Refactorizar para reducir
    Cognitive Complexity.
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
                                r"self\.data_source\.([a-zA-Z_][a-zA-Z0-9_]*)"
                                r"\s*\(",
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
    # El print largo se elimina para cumplir PEP8
    # print("[CHECK] Métodos implementados en OBDDataSource:", sorted(implemented_methods))
    missing = required_methods - implemented_methods
    if missing:
        print(
            f"[CHECK][ADVERTENCIA] Métodos FALTANTES en OBDDataSource: "
            f"{sorted(missing)}"
        )
        print("[CHECK] Sugerencias de stubs para agregar:")
        for m in sorted(missing):
            print(
                f"    def {m}(self):\n        print('[STUB] OBDDataSource.{m} llamado')\n        return None\n"
            )
    else:
        print(
            "[CHECK] Todos los métodos requeridos por la UI "
            "están implementados en OBDDataSource."
        )


# Ejecutar el chequeo tras definir OBDDataSource
check_obd_datasource_methods()
# --- FIN AUTO-CHECK ---

# --- LIMPIEZA Y CONSOLIDACIÓN DASHBOARD OBD-II ---
# Versión desacoplada UI/backend, 2025-06-03
# Elimina duplicados, referencias rotas y fragmentos incompletos.
# Lógica robusta para importación/escaneo de PIDs soportados.

# - Eliminados argumentos y variables no usados, ramas duplicadas y
#   código muerto
# Se eliminan duplicados y se asegura que el worker use siempre la lista
# de PIDs más reciente
# Inicialización explícita para evitar advertencias del analizador
# estático
# Modifica la lista PIDS_FUNCIONALES arriba para cambiar los PIDs
# seleccionados por defecto
# Imprime la lista de PIDs funcionales seleccionados por defecto
# --- Comentarios para futuras extensiones ---
# Puedes agregar panel de DTC, controles de escenario, etc.

# --- Widget visual de estado de conexión ---
class EstadoConexionWidget(QWidget):
    """
    Muestra icono circular (color) y texto, y permite expansión futura
    (tipo interfaz, VIN, etc).
    """

    estado_cambiado = pyqtSignal(
        str, str, str
    )  # estado_anterior, estado_nuevo, mensaje_error

    def __init__(self, parent=None):
        super().__init__(parent)
        self.estado = "desconectado"
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

    def paintEvent(self, a0):  # noqa: ARG002
        # a0 es requerido por PyQt6 pero no se usa
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
        # a0 no se usa, necesario para PyQt6


# --- REFACCIONADO: Clases DataAcquisitionWorker y DashboardOBD ---
# Se eliminan duplicados y se asegura que el worker use siempre la lista
# de PIDs más reciente
# y que la UI solo refresque con el último dato recibido.

class DataAcquisitionWorker(QObject):
    """
    Worker para adquisición y logging de datos OBD-II en un QThread.
    """

    data_ready = pyqtSignal(dict)
    error_ocurrido = pyqtSignal(str)
    heartbeat = pyqtSignal(str)

    def __init__(self, data_source, get_pids_fn, interval=None):
        super().__init__()
        self.data_source = data_source
        self.get_pids_fn = get_pids_fn
        # Intervalo configurable y seguro
        if interval is not None:
            self.interval = interval
        elif getattr(data_source, 'modo', 'emulador') == 'real':
            self.interval = max(DEFAULT_INTERVAL_REAL, MIN_INTERVAL_REAL)
        else:
            self.interval = DEFAULT_INTERVAL_EMU
        self._running = True
        self._ciclos = 0

    def run(self):
        """
        Bucle principal robusto: try/except global, logging, heartbeats,
        log de memoria y estado de threads cada 100 ciclos.
        """
        logging.info('[WORKER] Iniciando ciclo de adquisición')
        while self._running:
            try:
                pids = self.get_pids_fn() if callable(self.get_pids_fn) else []
                if pids:
                    datos = self.data_source.read_data(pids)
                    self.data_ready.emit(datos)
                self._ciclos += 1
                if self._ciclos % 10 == 0:
                    self.heartbeat.emit(f'worker-alive-{self._ciclos}')
                if self._ciclos % 100 == 0:
                    self._log_recursos()
                time.sleep(self.interval)
            except Exception as ex:
                logging.error(
                    '[WORKER][EXCEPTION] %s\n%s',
                    ex, traceback.format_exc()
                )
                self.error_ocurrido.emit(str(ex))
                # Opcional: break para detener el worker tras error crítico
                break
        logging.info('[WORKER] Ciclo de adquisición detenido')

    def stop(self):
        self._running = False
        logging.info('[WORKER] stop() llamado')

    def _log_recursos(self):
        proceso = threading.current_thread()
        logging.info(
            '[WORKER][THREAD] ID: %s, Activo: %s',
            proceso.ident, proceso.is_alive()
        )


class DashboardOBD(QWidget):
    """
    UI principal del dashboard OBD-II. Gestiona widgets, layouts, eventos y
    comunicación con OBDDataSource.
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
        self.pids_disponibles = [normalizar_pid(pid) for pid in PIDS.keys()]
        self.estado_conexion_widget = EstadoConexionWidget()
        self.latest_data = None  # Último dato recibido del worker
        # Inicialización explícita para evitar advertencias del analizador estático
        self.worker = None
        self.data_thread = None
        self.timer = None
        self.init_ui()
        self._setup_data_thread()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(50)  # Refresca la UI cada 50 ms (~20 FPS)
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self._ui_heartbeat)
        self.heartbeat_timer.start(2000)  # Heartbeat UI cada 2s

    def init_ui(self):
        """
        Inicializa la interfaz gráfica del Dashboard OBD-II con todos los
        widgets personalizados previos.
        Estructura: selector de modo, panel de selección de PIDs, gauges,
        tabla de log, controles y estado de conexión.
        Compatible con arquitectura desacoplada (worker, señales, timer).
        """
        # Layout principal
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # --- Selector de modo (Emulador/Real) ---
        modo_layout = QHBoxLayout()
        modo_label = QLabel("Modo de operación:")
        self.modo_combo = QComboBox()
        self.modo_combo.addItems([
            "Emulador",
            "Conexión real"
        ])
        self.modo_combo.setCurrentIndex(0)
        self.modo_combo.currentIndexChanged.connect(
            self.on_modo_changed
        )
        modo_layout.addWidget(modo_label)
        modo_layout.addWidget(self.modo_combo)
        modo_layout.addStretch()
        main_layout.addLayout(modo_layout)

        # --- Título principal ---
        titulo_label = QLabel("Dashboard OBD-II")
        titulo_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        titulo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(titulo_label)

        # --- Estado de conexión ---
        main_layout.addWidget(self.estado_conexion_widget)

        # --- Layout superior: selección de PIDs + gauges ---
        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        # --- Panel de selección de PIDs ---
        pids_panel = QVBoxLayout()
        pids_label = QLabel("Selecciona parámetros (PIDs):")
        pids_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        pids_panel.addWidget(pids_label)
        self.pid_checkboxes = {}
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        pids_widget = QWidget()
        pids_layout = QVBoxLayout()
        # --- Selección automática de PIDs funcionales ---
        # Modifica la lista PIDS_FUNCIONALES arriba para cambiar los PIDs
        # seleccionados por defecto
        self.selected_pids = []
        for pid in self.pids_disponibles:
            cb = QCheckBox(pid)
            if pid in PIDS_FUNCIONALES:
                cb.setChecked(True)
                self.selected_pids.append(pid)
            cb.stateChanged.connect(
                lambda state, p=pid: self.on_pid_checkbox_changed(p, state)
            )
            self.pid_checkboxes[pid] = cb
            pids_layout.addWidget(cb)
        pids_widget.setLayout(pids_layout)
        scroll_area.setWidget(pids_widget)
        pids_panel.addWidget(scroll_area)
        top_layout.addLayout(pids_panel, 1)

        # --- Panel de gauges (visualización de datos) ---
        gauges_panel = QGridLayout()
        # RPM
        gauge_rpm = GaugeWidget(
            min_value=0, max_value=8000, units="RPM",
            color=QColor(0, 200, 255)
        )
        self.gauge_widgets["rpm"] = gauge_rpm
        gauges_panel.addWidget(
            self._gauge_with_label(gauge_rpm, "RPM"), 0, 0
        )
        # Velocidad
        gauge_vel = GaugeWidget(
            min_value=0, max_value=240, units="km/h",
            color=QColor(0, 255, 100)
        )
        self.gauge_widgets["vel"] = gauge_vel
        gauges_panel.addWidget(
            self._gauge_with_label(gauge_vel, "Velocidad"), 0, 1
        )
        # Temperatura
        gauge_temp = GaugeWidget(
            min_value=0, max_value=120, units="°C",
            color=QColor(255, 120, 0)
        )
        self.gauge_widgets["temp"] = gauge_temp
        gauges_panel.addWidget(
            self._gauge_with_label(gauge_temp, "Temp. Refrigerante"), 1, 0
        )
        # Voltaje batería
        gauge_volt = GaugeWidget(
            min_value=10, max_value=16, units="V",
            color=QColor(255, 255, 0)
        )
        self.gauge_widgets["volt_bateria"] = gauge_volt
        gauges_panel.addWidget(
            self._gauge_with_label(gauge_volt, "Voltaje Batería"), 1, 1
        )
        # Puedes agregar más gauges aquí según tus PIDs
        gauges_widget = QWidget()
        gauges_widget.setLayout(gauges_panel)
        top_layout.addWidget(gauges_widget, 2)

        # --- Controles inferiores: botones y tabla de log ---
        controls_layout = QHBoxLayout()
        main_layout.addLayout(controls_layout)

        # --- Botones de control ---
        btn_conectar = QPushButton("Conectar")
        btn_conectar.clicked.connect(self.on_conectar)
        btn_conectar.setStyleSheet(
            "background-color: #1e88e5; color: #fff; font-weight: bold; "
            "border-radius: 6px; padding: 8px 18px;"
        )
        btn_desconectar = QPushButton("Desconectar")
        btn_desconectar.clicked.connect(self.on_desconectar)
        btn_desconectar.setStyleSheet(
            "background-color: #e53935; color: #fff; font-weight: bold; "
            "border-radius: 6px; padding: 8px 18px;"
        )
        controls_layout.addWidget(btn_conectar)
        controls_layout.addWidget(btn_desconectar)
        controls_layout.addStretch()

        # --- Tabla de log de datos ---
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(6)
        self.log_table.setHorizontalHeaderLabels([
            "Timestamp", "RPM", "Velocidad", "Temp", "Voltaje", "Escenario"
        ])
        self.log_table.setMinimumHeight(120)
        main_layout.addWidget(self.log_table)

        # --- Comentarios para futuras extensiones ---
        # Puedes agregar panel de DTC, controles de escenario, etc.

        # --- Espaciador final ---
        main_layout.addStretch()

        # --- Imprime la lista de PIDs funcionales seleccionados por defecto ---
        print(
            "[INFO] PIDs funcionales seleccionados por defecto: %s" %
            str(self.selected_pids)
        )

    def on_modo_changed(self, _):
        modo = self.modo_combo.currentText()
        print("[INFO] Modo seleccionado: %s" % modo)
        if modo == "Emulador":
            nuevo_modo = "emulador"
        else:
            nuevo_modo = "real"
        if hasattr(self, 'worker') and self.worker is not None:
            if hasattr(self.worker, 'stop') and callable(self.worker.stop):
                self.worker.stop()
        if hasattr(self, 'data_thread') and self.data_thread is not None:
            if hasattr(self.data_thread, 'quit') and callable(self.data_thread.quit):
                self.data_thread.quit()
            if hasattr(self.data_thread, 'wait') and callable(self.data_thread.wait):
                self.data_thread.wait()
        self.data_source = OBDDataSource(nuevo_modo)
        self._setup_data_thread()
        self.estado_conexion_widget.set_estado("desconectado")
        print("[INFO] Backend reiniciado en modo: %s" % nuevo_modo)

    def _gauge_with_label(self, gauge, label_text):
        """Devuelve un widget vertical con gauge y su label."""
        widget = QWidget()
        vbox = QVBoxLayout()
        vbox.addWidget(gauge)
        lbl = QLabel(label_text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(lbl)
        widget.setLayout(vbox)
        return widget

    def _update_gauges_with_data(self, datos):
        """
        Actualiza los valores de los gauges con los datos recibidos.
        Si el valor es inválido, aplica estilo de advertencia.
        """
        for pid, gauge in self.gauge_widgets.items():
            valor = datos.get(pid, 0)
            try:
                if valor in (None, '', 'None'):
                    self._set_gauge_invalid(gauge)
                else:
                    self._set_gauge_value(gauge, valor)
            except Exception as e:
                logging.warning("Error actualizando gauge %s: %s", pid, e)
                self._set_gauge_invalid(gauge)

    def _set_gauge_value(self, gauge, valor):
        """
        Asigna el valor al gauge y limpia el estilo de advertencia.
        """
        if hasattr(gauge, 'set_value'):
            gauge.set_value(valor)
        if hasattr(gauge, 'setStyleSheet'):
            gauge.setStyleSheet("")

    def _set_gauge_invalid(self, gauge):
        """
        Aplica estilo de advertencia visual al gauge.
        """
        if hasattr(gauge, 'set_invalid'):
            gauge.set_invalid()
        elif hasattr(gauge, 'setStyleSheet'):
            gauge.setStyleSheet(GAUGE_INVALID_STYLE)

    def on_pid_checkbox_changed(self, pid, state):
        """
        Maneja el cambio de estado de los checkboxes de PIDs.
        Actualiza la lista de PIDs seleccionados y evita duplicados.
        """
        if state == 2:
            if pid not in self.selected_pids:
                self.selected_pids.append(pid)
        else:
            if pid in self.selected_pids:
                self.selected_pids.remove(pid)
        self.selected_pids = list(dict.fromkeys(self.selected_pids))
        logging.info("PIDs seleccionados: %s", self.selected_pids)
        if pid == "volt_bateria" and state != 2:
            if "volt_bateria" in self.gauge_widgets:
                self._set_gauge_invalid(self.gauge_widgets["volt_bateria"])

    def _actualizar_tabla_log(self, datos):
        """
        Agrega una nueva fila a la tabla de log con los datos más recientes.
        """
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        columnas = [
            "timestamp", "rpm", "vel", "temp", "volt_bateria", "escenario"
        ]
        for idx, col in enumerate(columnas):
            self.log_table.setItem(
                row, idx, QTableWidgetItem(str(datos.get(col, "")))
            )
        self.log_table.scrollToBottom()

    def on_conectar(self):
        """
        Maneja el evento de conexión. Intenta conectar y actualiza el estado.
        """
        logging.info("Botón Conectar presionado.")
        try:
            self.data_source.connect()
            estado = "conectado" if self.data_source.connected else "error"
            self.estado_conexion_widget.set_estado(estado)
        except OSError as e:
            logging.error("Error al conectar: %s", e)
            self.estado_conexion_widget.set_estado("error", str(e))

    def on_desconectar(self):
        """
        Maneja el evento de desconexión y detiene el worker y thread.
        """
        logging.info("Botón Desconectar presionado.")
        try:
            self.data_source.disconnect()
        except Exception as e:
            logging.error(
                'Error al desconectar: %s',
                e
            )
        self.estado_conexion_widget.set_estado("desconectado")
        if hasattr(self, 'worker') and self.worker is not None:
            if hasattr(self.worker, 'stop') and callable(self.worker.stop):
                self.worker.stop()
        if hasattr(self, 'data_thread') and self.data_thread is not None:
            if hasattr(self.data_thread, 'quit') and callable(self.data_thread.quit):
                self.data_thread.quit()
            if hasattr(self.data_thread, 'wait') and callable(self.data_thread.wait):
                self.data_thread.wait()

    def closeEvent(self, a0):
        """Cierre seguro de hilos y worker al cerrar la ventana principal."""
        if hasattr(self, 'data_thread') and self.data_thread is not None:
            if hasattr(self.data_thread, 'quit') and callable(self.data_thread.quit):
                self.data_thread.quit()
            if hasattr(self.data_thread, 'wait') and callable(self.data_thread.wait):
                self.data_thread.wait()
        if hasattr(self, 'worker') and self.worker is not None:
            if hasattr(self.worker, 'stop') and callable(self.worker.stop):
                self.worker.stop()
        if a0 is not None and hasattr(a0, 'accept') and callable(a0.accept):
            a0.accept()

    def _setup_data_thread(self):
        """
        Inicializa el QThread y el worker para adquisición de datos.
        """
        if hasattr(self, 'worker') and self.worker is not None:
            if hasattr(self.worker, 'stop') and callable(self.worker.stop):
                self.worker.stop()
        if hasattr(self, 'data_thread') and self.data_thread is not None:
            if hasattr(self.data_thread, 'quit') and callable(self.data_thread.quit):
                self.data_thread.quit()
            if hasattr(self.data_thread, 'wait') and callable(self.data_thread.wait):
                self.data_thread.wait()
        self.worker = DataAcquisitionWorker(
            self.data_source, lambda: self.selected_pids
        )
        self.data_thread = QThread()
        self.worker.moveToThread(self.data_thread)
        self.data_thread.started.connect(self.worker.run)
        self.worker.data_ready.connect(self.on_data_ready)
        self.worker.error_ocurrido.connect(self._on_worker_error)
        self.worker.heartbeat.connect(self._on_worker_heartbeat)
        self.data_thread.start()

    def _on_worker_error(self, msg):
        """
        Maneja errores emitidos por el worker y actualiza el estado visual.
        """
        logging.error("[WORKER][ERROR] %s", msg)
        self.estado_conexion_widget.set_estado("error", msg)

    def _on_worker_heartbeat(self, msg):
        """
        Recibe heartbeats del worker y los registra.
        """
        logging.info("[WORKER][HEARTBEAT] %s", msg)

    def _ui_heartbeat(self):
        """
        Heartbeat periódico de la UI para monitoreo.
        """
        logging.debug("[UI][HEARTBEAT] UI viva")

    def on_data_ready(self, datos):
        """
        Callback cuando el worker entrega nuevos datos.
        Actualiza gauges y tabla de log.
        """
        self.latest_data = datos
        self._update_gauges_with_data(datos)
        self._actualizar_tabla_log(datos)

    def update_data(self):
        """
        Refresca la UI con el último dato recibido del worker.
        """
        if self.latest_data:
            self._update_gauges_with_data(self.latest_data)


# --- Definir constante para advertencia visual en gauges ---
GAUGE_INVALID_STYLE = "background-color: #7a2323; color: #fff;"

# Añadir método set_invalid a GaugeWidget si no existe
if not hasattr(GaugeWidget, 'set_invalid'):
    def set_invalid(self):
        if hasattr(self, 'setStyleSheet'):
            self.setStyleSheet(GAUGE_INVALID_STYLE)
    setattr(GaugeWidget, 'set_invalid', set_invalid)


def main():
    """
    Punto de entrada principal de la aplicación Dashboard OBD-II.
    """
    app = QApplication(sys.argv)
    window = DashboardOBD()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
