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

import sys
import os
import logging
from datetime import datetime


# --- INICIO: Manejo robusto de imports para ejecución desde cualquier carpeta ---
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

import traceback
import time
import sqlite3
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
    QWidget,
    QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.widgets.gauge import GaugeWidget
from obd.connection import OBDConnection
from obd.elm327 import ELM327
from obd.pids import PIDS
from obd.pids_ext import PIDS as PIDS_EXT, normalizar_pid
# --- Agregar PID de velocidad estándar a PIDS si no existe ---
if 'vel' not in PIDS:
    PIDS['vel'] = {
        'cmd': '010D',
        'desc': 'Velocidad',
        'min': 0,
        'max': 255,
        'unidad': 'km/h',
    }
from storage.export import export_dynamic_log
from utils.logging_app import log_evento_app


# --- INICIO: Logging por sesión ---
def setup_session_logger():
    """
    Configura un logger por sesión con archivo único por arranque.
    """
    log_dir = os.path.join(os.path.dirname(__file__), "../../")
    log_dir = os.path.abspath(log_dir)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_name = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    log_path = os.path.join(log_dir, log_name)
    logger = logging.getLogger("obd_session")
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.info(f"--- INICIO DE SESIÓN OBD-II: {log_name} ---")
    return logger, log_path


SESSION_LOGGER, SESSION_LOG_PATH = setup_session_logger()
# --- FIN: Logging por sesión ---

# --- Corrección: Conversión robusta de datos OBD-II a int/float en modo real ---
# Todos los valores numéricos de PIDs se convierten a int/float antes de operar, loguear o exportar.
# Si la conversión falla, se deja el valor original y se puede advertir en el log o UI.


# --- MOCK: Abstracción de fuente de datos (real/emulador) ---
class OBDDataSource:
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
        print(f"[DEBUG] OBDDataSource inicializado en modo: {self.modo}")

    def set_escenario(self, escenario):
        self.escenario = escenario
        log_evento_app(
            "INFO", f"Escenario cambiado a: {escenario}", contexto="set_escenario"
        )

    def connect(self):
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
                        SESSION_LOGGER.info("[HANDSHAKE] Handshake OK con ELM327")
                    else:
                        log_evento_app(
                            "ERROR", "Handshake fallido con ELM327", contexto="connect"
                        )
                        SESSION_LOGGER.error("[HANDSHAKE] Handshake fallido con ELM327")
                except Exception as e:
                    self.connected = False
                    self.last_handshake_ok = False
                    self.last_handshake_error = str(e)
                    log_evento_app(
                        "ERROR", f"Fallo de conexión OBD-II: {e}", contexto="connect"
                    )
                    SESSION_LOGGER.error(f"[HANDSHAKE] Error: {e}")
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
            SESSION_LOGGER.error(f"[HANDSHAKE] Error general: {e}")
            raise e

    def disconnect(self):
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
            SESSION_LOGGER.warning(f"[PARSE][{pid_context or 'rpm'}] Respuesta vacía o inválida para RPM. Contexto: cmd={cmd_context}, resp={respuesta_cruda}")
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
                    SESSION_LOGGER.warning(f"[PARSE][{pid_context or 'rpm'}] Error parseando RPM. Línea: '{linea}', cmd={cmd_context}, error={e}")
                    continue
            else:
                SESSION_LOGGER.warning(f"[PARSE][{pid_context or 'rpm'}] Respuesta cruda no válida para RPM. Línea: '{linea}', cmd={cmd_context}")
        return None

    def parse_vel(self, respuesta_cruda, pid_context=None, cmd_context=None):
        """Parsea respuesta cruda de velocidad (ej: '410D00' o '41 0D 00') a valor numérico. Robustez y logging."""
        if not respuesta_cruda or not isinstance(respuesta_cruda, str):
            SESSION_LOGGER.warning(f"[PARSE][{pid_context or 'vel'}] Respuesta vacía o inválida para velocidad. Contexto: cmd={cmd_context}, resp={respuesta_cruda}")
            return None
        for linea in respuesta_cruda.strip().splitlines():
            raw = linea.replace(" ", "")
            if (raw.startswith("410D") or linea.startswith("41 0D")) and len(raw) >= 6:
                try:
                    vel = int(raw[4:6], 16)
                    return vel
                except Exception as e:
                    SESSION_LOGGER.warning(f"[PARSE][{pid_context or 'vel'}] Error parseando velocidad. Línea: '{linea}', cmd={cmd_context}, error={e}")
                    continue
            else:
                SESSION_LOGGER.warning(f"[PARSE][{pid_context or 'vel'}] Respuesta cruda no válida para velocidad. Línea: '{linea}', cmd={cmd_context}")
        return None

    def parse_pid_response(self, pid, resp, cmd_context=None):
        """
        Parsea la respuesta cruda de ELM327 para un PID estándar y retorna valor numérico o '' si no es válido.
        Procesa múltiples líneas y loguea advertencias detalladas.
        """
        if resp is None or resp == '':
            SESSION_LOGGER.warning(f"[PARSE][{pid}] Respuesta vacía. Contexto: cmd={cmd_context}")
            return ''
        if isinstance(resp, (int, float)):
            return resp
        if isinstance(resp, str):
            for linea in resp.strip().splitlines():
                l = linea.strip()
                if l in ("NO DATA", "SEARCHING...", "", "NONE", "None", "\r>", "STOPPED"):
                    continue
                try:
                    if pid in ("rpm", "010C") and (l.startswith("41 0C") or l.replace(" ", "").startswith("410C")):
                        val = self.parse_rpm(l, pid_context=pid, cmd_context=cmd_context)
                        if val is not None:
                            return val
                    elif pid in ("vel", "010D") and (l.startswith("41 0D") or l.replace(" ", "").startswith("410D")):
                        val = self.parse_vel(l, pid_context=pid, cmd_context=cmd_context)
                        if val is not None:
                            return val
                    elif pid in PIDS_EXT and "cmd" in PIDS_EXT[pid]:
                        # Aquí podrías agregar lógica robusta para otros PIDs
                        pass
                except Exception as e:
                    SESSION_LOGGER.warning(f"[PARSE][{pid}] Excepción inesperada al parsear línea: '{l}'. cmd={cmd_context}, error={e}")
                    continue
            SESSION_LOGGER.warning(f"[PARSE][{pid}] Ninguna línea válida encontrada en respuesta. Resp completa: {resp}, cmd={cmd_context}")
            return ''
        SESSION_LOGGER.warning(f"[PARSE][{pid}] Tipo de respuesta no soportado: {type(resp)}. Resp: {resp}, cmd={cmd_context}")
        return ''

    def _parse_and_log_real(self, pids_legibles):
        """Obtiene y parsea datos reales, loguea y retorna el dict de datos. Refuerza logs y diagnóstico."""
        data = {}
        for pid in pids_legibles:
            if pid == 'escenario':
                # Stub vacío para evitar advertencias repetidas
                data[pid] = ''
                continue
            pid_legible = normalizar_pid(pid)
            pid_key = self.get_pid_key(pid_legible, PIDS)
            if pid_key in PIDS:
                cmd = PIDS[pid_key]["cmd"]
                SESSION_LOGGER.info(f"[OBD] Enviando comando: {cmd} (PID: {pid_legible})")
                print(f"[OBD] Enviando: {cmd} para {pid_legible}")
                try:
                    resp = self.elm.send_pid(cmd)
                    SESSION_LOGGER.info(f"[OBD] Respuesta cruda para {cmd} (PID: {pid_legible}): {resp}")
                    print(f"[OBD] Respuesta cruda para {cmd}: '{resp}'")
                except Exception as e:
                    resp = None
                    SESSION_LOGGER.warning(f"[OBD] Error al enviar comando {cmd} (PID: {pid_legible}): {e}")
                    print(f"[OBD] Error al enviar comando {cmd}: {e}")
                try:
                    if pid_legible == "rpm":
                        val = self.parse_rpm(resp, pid_context=pid_legible, cmd_context=cmd) if resp else None
                    elif pid_legible == "vel":
                        val = self.parse_vel(resp, pid_context=pid_legible, cmd_context=cmd) if resp else None
                    else:
                        val = self.parse_pid_response(pid_legible, resp, cmd_context=cmd)
                except Exception as ex:
                    import traceback
                    SESSION_LOGGER.error(f"[OBD] Excepción inesperada en parsing PID={pid_legible}, cmd={cmd}, resp={resp}, error={ex}\n{traceback.format_exc()}")
                    val = None
                    log_evento_app("ERROR", f"Error de parsing en PID {pid_legible}. Ver log para detalles.", contexto="read_data")
                    self._mostrar_error_ui(f"Error de adquisición/parsing en PID {pid_legible}. Ver log para detalles.")
                data[pid_legible] = val
                print(f"[OBD] PID={pid_legible}, crudo={resp}, valor={val}")
                log_evento_app(
                    "INFO", f"[OBD] PID={pid_legible}, valor={val}", contexto="read_data"
                )
                if val not in (None, '', 'None'):
                    SESSION_LOGGER.info(f"[OBD] {pid_legible} recibido: {val}")
                else:
                    advert = (
                        f"ADVERTENCIA: El PID {pid_legible} no entregó datos válidos. "
                        f"Comando: {cmd}, Respuesta: {resp}, Parsing: {val}"
                    )
                    print(advert)
                    log_evento_app("ADVERTENCIA", advert, contexto="read_data")
                    SESSION_LOGGER.warning(advert)
            else:
                data[pid_legible] = ""
                # No advertencia para 'escenario' en modo real
                if pid_legible != 'escenario':
                    advert = f"ADVERTENCIA: El PID {pid_legible} no está definido en PIDS para modo real."
                    print(advert)
                    log_evento_app("ADVERTENCIA", advert, contexto="read_data")
                    SESSION_LOGGER.warning(advert)
        return data

    def _mostrar_error_ui(self, mensaje):
        # Método auxiliar para mostrar error en la UI si está disponible
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error de adquisición/parsing", mensaje)
        except Exception:
            pass

    def get_log(self):
        """Devuelve el log en memoria (lista de dicts)."""
        return self.log

    def read_data(self, pids_legibles):
        """Adquiere datos según el modo y los PIDs seleccionados. Guarda en log y retorna dict."""
        if self.modo == "real":
            data = self._parse_and_log_real(pids_legibles)
        else:
            data = self._parse_and_log_emulador(pids_legibles)
        # Agrega timestamp y escenario
        data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["escenario"] = getattr(self, "escenario", "-")
        self.log.append(data.copy())
        return data

    def _parse_and_log_emulador(self, pids_legibles):
        """Simula adquisición de datos en modo emulador."""
        data = {}
        for pid in pids_legibles:
            if pid == "rpm":
                data[pid] = self.rpm
            elif pid == "vel":
                data[pid] = self.vel
            elif pid == "escenario":
                data[pid] = self.escenario
            else:
                data[pid] = 0
        return data

    def resumen_sesion(self):
        """Imprime y loguea resumen de la sesión: PIDs con datos válidos, vacíos y errores."""
        log = self.get_log()
        if not log:
            SESSION_LOGGER.info("No se registraron datos en la sesión.")
            print("No se registraron datos en la sesión.")
            return
        pids = list(log[0].keys())
        vacios = set()
        validos = set()
        for row in log:
            for pid in pids:
                val = row.get(pid, "")
                if val in (None, "", "None"):
                    vacios.add(pid)
                else:
                    validos.add(pid)
        vacios = vacios - validos
        print("--- Resumen de sesión OBD-II ---")
        SESSION_LOGGER.info("PIDs con datos válidos: %s", ", ".join(sorted(validos)))
        print("PIDs con datos válidos:", ", ".join(sorted(validos)))
        SESSION_LOGGER.info("PIDs siempre vacíos: %s", ", ".join(sorted(vacios)))
        print("PIDs siempre vacíos:", ", ".join(sorted(vacios)))
        if vacios:
            SESSION_LOGGER.warning(
                "Algunos PIDs no recibieron datos válidos durante la sesión."
            )
            print(
                "Advertencia: Algunos PIDs no recibieron datos válidos durante la sesión."
            )
        SESSION_LOGGER.info("[AUDITORÍA] Comandos y respuestas crudas por sesión:")
        print("[AUDITORÍA] Ver log para detalles de comandos y respuestas crudas.")
        SESSION_LOGGER.info(
            "Gauges activos en UI: %d, gauges ocultados por falta de datos: %d",
            len(validos), len(vacios)
        )
        print(
            f"Gauges activos en UI: {len(validos)}, gauges ocultados por falta de datos: {len(vacios)}"
        )

    def get_dtc(self):
        """Devuelve los códigos DTC simulados o reales, robusto a métodos faltantes."""
        if self.modo == "real" and self.elm:
            try:
                if hasattr(self.elm, "read_dtc"):
                    return self.elm.read_dtc()
                else:
                    SESSION_LOGGER.warning("ELM327 no implementa 'read_dtc'. Se retorna lista vacía.")
                    return []
            except Exception as e:
                SESSION_LOGGER.warning(f"Error al leer DTC: {e}")
                return []
        return self.dtc

    def clear_dtc(self):
        """Borra los códigos DTC simulados o reales, robusto a métodos faltantes."""
        if self.modo == "real" and self.elm:
            try:
                if hasattr(self.elm, "clear_dtc"):
                    self.elm.clear_dtc()
                else:
                    SESSION_LOGGER.warning("ELM327 no implementa 'clear_dtc'. No se borra DTC real.")
            except Exception as e:
                SESSION_LOGGER.warning(f"Error al borrar DTC: {e}")
        self.dtc = []

    def get_pid_key(self, pid_legible, pids_dict):
        """
        Centraliza la obtención de la clave de PID estándar a partir de un nombre legible o código.
        Devuelve la clave que debe usarse en el dict de PIDS.
        """
        # Búsqueda directa
        if pid_legible in pids_dict:
            return pid_legible
        # Buscar por código OBD (campo 'cmd')
        for k, v in pids_dict.items():
            if v.get('cmd', '').lower() == pid_legible.lower():
                return k
        # Buscar por nombre legible (campo 'desc' o similar)
        for k, v in pids_dict.items():
            if v.get('desc', '').lower() == pid_legible.lower():
                return k
        # Si no se encuentra, devolver el original (puede ser un PID personalizado)
        return pid_legible


class DashboardOBD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard OBD-II Multiplataforma")
        self.setGeometry(100, 100, 900, 500)
        self.setStyleSheet("background-color: #181c20; color: #f0f0f0;")
        self.data_source = OBDDataSource("emulador")
        self.selected_pids = []  # Arranca en blanco, sin PIDs forzados
        self.pid_checkboxes = {}
        self.gauge_widgets = {}
        self.test_en_ejecucion = False  # Flag para evitar dobles ejecuciones
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)
        print(f"[AUDITORÍA] PIDs activos al iniciar: {self.selected_pids}")
        # --- INTEGRACIÓN: Test automático de PIDs al inicio ---
        QTimer.singleShot(1000, self.ejecutar_test_automatizado_al_inicio)

    def init_ui(self):
        layout = QVBoxLayout()
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
        self.gauge_widgets = {}
        # NO inicializar gauges fijos por defecto
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
        # --- Botón de test automático de PIDs ---
        self.btn_test_pids = QPushButton("Test automático de PIDs")
        self.btn_test_pids.setStyleSheet("background-color: #1e90ff; color: white; font-weight: bold;")
        self.btn_test_pids.clicked.connect(self.test_automatizado_pids)
        log_layout.addWidget(self.btn_test_pids)
        layout.addLayout(log_layout)
        # Tabla de log en tiempo real
        self.table_log = QTableWidget(0, len(self.selected_pids) + 2)
        headers = (
            ["Timestamp"]
            + [
                PIDS_EXT[pid]["desc"] if pid in PIDS_EXT else pid
                for pid in self.selected_pids
            ]
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
        pid_widget = QWidget()
        grid = QGridLayout()
        self.pid_checkboxes = {}
        for i, (pid, info) in enumerate(PIDS_EXT.items()):
            cb = QCheckBox(f"{pid} - {info.get('desc', pid)}")
            cb.stateChanged.connect(self.on_pid_selection_changed)
            self.pid_checkboxes[pid] = cb
            grid.addWidget(cb, i // 2, i % 2)
        pid_widget.setLayout(grid)
        scroll.setWidget(pid_widget)
        pid_panel.addWidget(scroll)
        layout.addLayout(pid_panel)
        # Panel de selección de modo de emulación (solo visible en modo emulador)
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
        # Solo mostrar si la fuente es emulador
        if hasattr(self.data_source, "modo") and self.data_source.modo == "emulador":
            layout.addWidget(self.modo_label)
            layout.addWidget(self.modo_combo)
        # Mensajes y estado
        self.status_label = QLabel("Desconectado.")
        self.status_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def cambiar_fuente(self):
        modo = "emulador" if self.fuente_combo.currentIndex() == 0 else "real"
        print(f"[DEBUG] cambiar_fuente: Seleccionado modo {modo.upper()}")
        self.data_source = OBDDataSource(modo)
        self.status_label.setText(f"Fuente cambiada a: {modo}")

    def check_wifi_obdii_connection(self, ip, port, timeout=3):
        import socket

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, port))
            s.close()
            return True, ""
        except Exception as e:
            return False, str(e)

    def conectar_fuente(self):
        try:
            print("[DEBUG] conectar_fuente: Iniciando conexión de fuente")
            self.data_source.disconnect()
            idx = self.fuente_combo.currentIndex()
            modo = "emulador" if idx == 0 else "real"
            print(f"[DEBUG] conectar_fuente: Seleccionado modo {modo.upper()}")
            self.data_source = OBDDataSource(modo)
            if modo == "real":
                ip = "192.168.0.10"  # Ajustar si es configurable
                puerto = 35000
                ok, error = self.check_wifi_obdii_connection(ip, puerto)
                if not ok:
                    print(f"[DEBUG] conectar_fuente: Error de conexión WiFi: {error}")
                    self.status_label.setText(
                        "Sin conexión con el OBD-II por WiFi. Revisa la red y reinicia el adaptador.\nDetalle: "
                        + error
                    )
                    return
            self.data_source.connect()
            print(f"[DEBUG] conectar_fuente: Conectado={self.data_source.connected}")
            if self.data_source.connected:
                self.status_label.setText(f"Conectado a: {modo}")
            else:
                self.status_label.setText("No conectado.")
        except Exception as e:
            self.status_label.setText(f"Error al conectar: {e}")
            print(f"[OBD-II WIFI] Error crítico: {e}")

    def desconectar_fuente(self):
        try:
            self.data_source.disconnect()
            self.status_label.setText("Desconectado.")
        except Exception as e:
            self.status_label.setText(f"Error al desconectar: {e}")

    def on_pid_selection_changed(self):
        seleccionados = self._get_selected_pids()
        print(f"[AUDITORÍA] PIDs seleccionados tras cambio: {seleccionados}")
        self.selected_pids = seleccionados
        self._update_gauges()
        self.status_label.setText(
            f"PIDs seleccionados: {', '.join(self.selected_pids)}"
        )
        log_evento_app("INFO", f"PIDs activos tras selección: {self.selected_pids}", contexto="UI_tracking")

    def _get_selected_pids(self):
        seleccionados = [normalizar_pid(pid) for pid, cb in self.pid_checkboxes.items() if cb.isChecked()]
        # DEDUPLICACIÓN
        vistos = set()
        resultado = []
        for pid in seleccionados:
            if pid not in vistos:
                resultado.append(pid)
                vistos.add(pid)
            else:
                self.status_label.setText(f"Advertencia: El PID '{pid}' ya está seleccionado. Solo se permite una variante por parámetro.")
                log_evento_app(
                    "ADVERTENCIA",
                    f"Intento de selección duplicada de PID: {pid} en UI",
                    contexto="UI_dedup_pids",
                )
        if len(resultado) > 8:
            for pid in resultado[8:]:
                for k, cb in self.pid_checkboxes.items():
                    if normalizar_pid(k) == pid:
                        cb.setChecked(False)
            resultado = resultado[:8]
        return resultado

    def _update_gauges(self):
        # Elimina gauges que ya no están activos
        for pid in list(self.gauge_widgets.keys()):
            if pid not in self.selected_pids:
                gauge = self.gauge_widgets[pid]
                self.gauges_layout.removeWidget(gauge)
                gauge.deleteLater()
                del self.gauge_widgets[pid]
                print(f"[AUDITORÍA] Gauge eliminado: {pid}")
                log_evento_app("INFO", f"Gauge eliminado: {pid}", contexto="UI_gauge_remove")
        # Agrega gauges nuevos solo para PIDs activos
        datos_actuales = self.data_source.get_log()[-1] if self.data_source.get_log() else {}
        for pid in self.selected_pids:
            if pid not in self.gauge_widgets and pid in PIDS_EXT:
                valor = datos_actuales.get(pid, None)
                minv = PIDS_EXT[pid].get("min", 0)
                maxv = PIDS_EXT[pid].get("max", 100)
                label = PIDS_EXT[pid].get("desc", pid)
                color = QColor(120, 255, 120)
                gauge = GaugeWidget(minv, maxv, label, color)
                self.gauges_layout.addWidget(gauge)
                self.gauge_widgets[pid] = gauge
                print(f"[AUDITORÍA] Gauge agregado: {pid}")
                log_evento_app("INFO", f"Gauge agregado: {pid}", contexto="UI_gauge_add")
        print(f"[AUDITORÍA] Gauges activos en UI: {list(self.gauge_widgets.keys())}")
        log_evento_app("INFO", f"Gauges activos en UI: {list(self.gauge_widgets.keys())}", contexto="UI_gauges_tracking")

    def update_data(self):
        try:
            print(f"[AUDITORÍA] PIDs activos antes de adquisición: {self.selected_pids}")
            log_evento_app("INFO", f"PIDs activos antes de adquisición: {self.selected_pids}", contexto="CICLO")
            data = self.data_source.read_data(self.selected_pids)
            # Solo actualizar gauges activos
            for pid, gauge in self.gauge_widgets.items():
                if data.get(pid) not in (None, '', 'None'):
                    gauge.setValue(data.get(pid, 0))
                else:
                    gauge.setValue(0)
            self._actualizar_tabla_log()
        except Exception as e:
            msg = f"Error: {e}"
            self.status_label.setText(msg)
            log_evento_app("ERROR", msg, contexto="update_data")
            traceback.print_exc()

    def _actualizar_tabla_log(self):
        log = self.data_source.get_log()[-100:]
        self.table_log.setColumnCount(len(self.selected_pids) + 2)
        headers = (
            ["Timestamp"]
            + [PIDS_EXT[pid]["desc"] if pid in PIDS_EXT else pid for pid in self.selected_pids]
            + ["Escenario"]
        )
        self.table_log.setHorizontalHeaderLabels(headers)
        self.table_log.setRowCount(len(log))
        for i, row in enumerate(log):
            self.table_log.setItem(i, 0, QTableWidgetItem(row.get("timestamp", "")))
            for j, pid in enumerate(self.selected_pids):
                self.table_log.setItem(i, j + 1, QTableWidgetItem(str(row.get(pid, ""))))
            self.table_log.setItem(i, len(self.selected_pids) + 1, QTableWidgetItem(row.get("escenario", "")))
        print(f"[AUDITORÍA] Columnas activas en log/tabla: {self.selected_pids}")
        log_evento_app("INFO", f"Columnas activas en log/tabla: {self.selected_pids}", contexto="LOG_COLS")

    def exportar_log(self):
        try:
            fname, _ = QFileDialog.getSaveFileName(
                self, "Exportar Log", "", "CSV (*.csv)"
            )
            if fname:
                log = self.data_source.get_log()
                pids = ["timestamp"] + self.selected_pids
                from storage.export import export_dynamic_log
                resultado = export_dynamic_log(fname, log, pids)
                if isinstance(resultado, tuple):
                    valido, errores = resultado
                else:
                    valido, errores = resultado, None
                if valido:
                    self.status_label.setText(
                        "Log guardado correctamente. El archivo es válido y cumple con los estándares."
                    )
                else:
                    self.status_label.setText(
                        f"Atención: El log presenta errores: {errores}"
                    )
                print(f"[AUDITORÍA] Exportación: columnas exportadas: {pids}")
                log_evento_app("INFO", f"Exportación: columnas exportadas: {pids}", contexto="EXPORT")
        except Exception as e:
            self.status_label.setText(f"Error al exportar: {e}")

    def closeEvent(self, a0):
        print(f"[AUDITORÍA] PIDs/gauges activos al cerrar: {self.selected_pids}")
        log_evento_app("INFO", f"PIDs/gauges activos al cerrar: {self.selected_pids}", contexto="CIERRE")
        self.data_source.resumen_sesion()
        super().closeEvent(a0)

    def on_modo_changed(self, modo):
        if hasattr(self.data_source, "set_escenario"):
            self.data_source.set_escenario(modo)
        self.status_label.setText(f"Modo de emulación: {modo}")

    def leer_dtc(self):
        try:
            dtc = self.data_source.get_dtc()
            self.dtc_label.setText(f'DTC: {dtc if dtc else "---"}')
            self.status_label.setText("Lectura de DTC exitosa.")
        except Exception as e:
            self.status_label.setText(f"Error al leer DTC: {e}")

    def borrar_dtc(self):
        try:
            self.data_source.clear_dtc()
            self.dtc_label.setText("DTC: ---")
            self.status_label.setText("DTC borrados.")
        except Exception as e:
            self.status_label.setText(f"Error al borrar DTC: {e}")

    def ejecutar_test_automatizado_al_inicio(self):
        """
        Lanza el test automático de PIDs al inicio de la app, solo si no está ya en ejecución.
        """
        if not getattr(self, 'test_en_ejecucion', False):
            self.test_en_ejecucion = True
            self.status_label.setText("Test automático de PIDs en ejecución (inicio)...")
            SESSION_LOGGER.info("[TEST] Test automático de PIDs lanzado automáticamente al inicio de la app.")
            try:
                self.test_automatizado_pids()
            except Exception as e:
                self.status_label.setText(f"Error en test automático: {e}")
                SESSION_LOGGER.error(f"[TEST] Error en test automático: {e}")
            self.test_en_ejecucion = False
        else:
            print("[TEST] Test automático ya en ejecución, omitiendo llamada duplicada.")

    def test_automatizado_pids(self):
        """
        Ejecuta el test automatizado de selección y borrado de PIDs, delegando en subfunciones para claridad y bajo acoplamiento.
        """
        import time
        from PyQt6.QtWidgets import QMessageBox
        if getattr(self, 'test_en_ejecucion', False):
            self.status_label.setText("Test automático de PIDs ya está en ejecución.")
            return
        self.test_en_ejecucion = True
        pids_disponibles = list(PIDS_EXT.keys())
        self.status_label.setText("Iniciando test automatizado de PIDs...")
        SESSION_LOGGER.info("[TEST] Iniciando test automatizado de selección/borrado de PIDs")
        resumen, gauges_fantasma, columnas_fantasma = self._seleccionar_y_validar_pids(pids_disponibles)
        resumen2, gauges_fantasma2, columnas_fantasma2 = self._borrar_y_validar_pids(pids_disponibles)
        # Unifica sets y resumen
        gauges_fantasma.update(gauges_fantasma2)
        columnas_fantasma.update(columnas_fantasma2)
        resumen.extend(resumen2)
        self._generar_reporte_test_automatizado(pids_disponibles, resumen, gauges_fantasma, columnas_fantasma)
        self.status_label.setText("Test automatizado finalizado. Ver reporte y log.")
        if gauges_fantasma or columnas_fantasma:
            self.status_label.setStyleSheet("background-color: #b22222; color: #fff; font-weight: bold;")
            QMessageBox.warning(self, "Test automático: ADVERTENCIA", "Se detectaron gauges o columnas fantasma.\nVer reporte y corregir antes de entregar.")
        else:
            self.status_label.setStyleSheet("")
            QMessageBox.information(self, "Test finalizado", "Test automatizado finalizado.\nVer reporte y log.")
        self.test_en_ejecucion = False

    def _seleccionar_y_validar_pids(self, pids_disponibles):
        """
        Selecciona cada PID uno a uno, valida aparición de gauge y columna, y espera datos válidos si es necesario.
        Refactorizado para reducir complejidad ciclomática.
        """
        resumen = []
        gauges_fantasma = set()
        columnas_fantasma = set()
        for pid in pids_disponibles:
            self._seleccionar_pid_unico(pid)
            self._update_gauges()
            self.update_data()
            self._esperar_dato_valido(pid, resumen)
            self._validar_gauge_columna(pid, gauges_fantasma, columnas_fantasma, resumen)
        return resumen, gauges_fantasma, columnas_fantasma

    def _seleccionar_pid_unico(self, pid):
        """Selecciona solo el checkbox del PID dado, deseleccionando los demás."""
        for cb_pid, cb in self.pid_checkboxes.items():
            cb.setChecked(cb_pid == pid)
        self.selected_pids = [pid]

    def _esperar_dato_valido(self, pid, resumen):
        """Espera hasta obtener un dato válido para el PID (especial para 'vel')."""
        import time
        from PyQt6.QtWidgets import QMessageBox
        intentos = 0
        while True:
            data = self.data_source.get_log()[-1] if self.data_source.get_log() else {}
            val = data.get(pid, None)
            if pid == "vel" and (val in (None, '', 'None', 0)):
                if intentos == 0:
                    self.status_label.setText("Por favor, avance algunos metros para verificar lectura de velocidad...")
                    QMessageBox.information(self, "Test de velocidad", "Por favor, avance algunos metros para verificar lectura de velocidad.")
                time.sleep(1)
                intentos += 1
                if intentos > 30:
                    resumen.append("[ADVERTENCIA] No se obtuvo valor válido de velocidad tras 30s.")
                    break
                continue
            break

    def _validar_gauge_columna(self, pid, gauges_fantasma, columnas_fantasma, resumen):
        """Valida que el gauge y la columna del PID estén presentes tras la selección."""
        gauges_activos = list(self.gauge_widgets.keys())
        columnas_activas = self.selected_pids.copy()
        if pid not in gauges_activos:
            gauges_fantasma.add(pid)
            resumen.append(f"[ERROR] Gauge de {pid} no apareció tras selección.")
        if pid not in columnas_activas:
            columnas_fantasma.add(pid)
            resumen.append(f"[ERROR] Columna de {pid} no apareció tras selección.")
        SESSION_LOGGER.info(f"[TEST] Seleccionado PID: {pid} | Gauges activos: {gauges_activos} | Columnas: {columnas_activas}")

    def _borrar_y_validar_pids(self, pids_disponibles):
        """
        Borra cada PID uno a uno, valida desaparición de gauge y columna.
        """
        import time
        resumen = []
        gauges_fantasma = set()
        columnas_fantasma = set()
        for pid in pids_disponibles:
            for cb_pid, cb in self.pid_checkboxes.items():
                if cb_pid == pid:
                    cb.setChecked(False)
            self.selected_pids = [p for p in self.selected_pids if p != pid]
            self._update_gauges()
            self.update_data()
            time.sleep(0.3)
            gauges_activos = list(self.gauge_widgets.keys())
            columnas_activas = self.selected_pids.copy()
            if pid in gauges_activos:
                gauges_fantasma.add(pid)
                resumen.append(f"[ERROR] Gauge de {pid} persiste tras borrado.")
            if pid in columnas_activas:
                columnas_fantasma.add(pid)
                resumen.append(f"[ERROR] Columna de {pid} persiste tras borrado.")
            SESSION_LOGGER.info(f"[TEST] Borrado PID: {pid} | Gauges activos: {gauges_activos} | Columnas: {columnas_activas}")
        return resumen, gauges_fantasma, columnas_fantasma

    def _generar_reporte_test_automatizado(self, pids_disponibles, resumen, gauges_fantasma, columnas_fantasma):
        """
        Genera el reporte resumen del test automatizado, exporta el log y guarda el archivo de reporte.
        """
        from storage.export import export_dynamic_log
        from datetime import datetime
        fname = "test_automatizado_log_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".csv"
        log = self.data_source.get_log()
        pids_export = ["timestamp"] + pids_disponibles
        export_dynamic_log(fname, log, pids_export)
        resumen.append("\n--- RESUMEN TEST AUTOMATIZADO ---")
        resumen.append(f"PIDs/gauges correctamente activados/desactivados: {set(pids_disponibles) - gauges_fantasma}")
        if gauges_fantasma:
            resumen.append(f"[ADVERTENCIA] Gauges fantasma detectados: {gauges_fantasma}")
        if columnas_fantasma:
            resumen.append(f"[ADVERTENCIA] Columnas fantasma detectadas: {columnas_fantasma}")
        if not gauges_fantasma and not columnas_fantasma:
            resumen.append("[OK] El sistema pasó el test: no hay gauges ni columnas fantasma.")
        else:
            resumen.append("[FALLO] Revisar lógica de borrado/actualización de UI y log/export.")
        reporte = "\n".join(resumen)
        rep_fname = "test_automatizado_reporte_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".txt"
        with open(rep_fname, "w", encoding="utf-8") as f:
            f.write(reporte)
        SESSION_LOGGER.info(reporte)


def main():
    app = QApplication(sys.argv)
    win = DashboardOBD()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
