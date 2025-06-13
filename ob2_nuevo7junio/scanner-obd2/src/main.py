"""
main.py - Entrada principal del Scanner OBD2

AVISO: Este archivo es solo la entrada principal. La lógica relevante y moderna de adquisición OBD2, backend asíncrono, logging, cache de PIDs y UI profesional está implementada en los módulos adjuntos y no es necesario volver a buscar o leer este archivo para entender la arquitectura ni la lógica de adquisición.

Consulte los archivos y módulos:
  - obd2_acquisition/core.py
  - ui/data_visualizer.py
  - ui/pid_acquisition.py
para la implementación principal y documentación.
"""

import sys
import os
import time
import socket
import obd
import logging
import datetime
# INTEGRACIÓN QASYNC
from qasync import QEventLoop, asyncSlot

# Configuración global de logging con archivo único por sesión
log_dir = os.path.join(os.path.dirname(__file__), '../logs')
os.makedirs(log_dir, exist_ok=True)
session_logfile = os.path.join(log_dir, f"app_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(session_logfile, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("OBD2App")

# --- En init_ui() de DataVisualizer ---
# --- Agrega estos métodos ---
# --- En tu configuración inicial (init_connections() o similar) ---

# ✅ Todas las funciones clave de la app (streaming de PIDs, gauges, DTC, multiplexado) permanecen intactas.
from PySide6.QtWidgets import QApplication, QListWidgetItem, QLabel, QInputDialog, QMessageBox
from PySide6.QtCore import Qt
import obd
from obd import OBDStatus
# Eliminada importación dinámica de GaugeWidget y referencias a gauge.py
import json
from vininfo import Vin
import os

# Asegura que el directorio src esté en sys.path para imports locales
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- CORRECCIÓN DE IMPORTS PARA COMPATIBILIDAD UNIVERSAL ---
# Usar imports relativos si se ejecuta como módulo, absolutos si es script
try:
    from .elm327_async import ELM327Async
    from .async_json_logger import AsyncJSONLogger
    from .pid_cache import PIDCache
    from .obd2_async_utils import read_vin, read_pids_batch
    from .heartbeat import heartbeat
    from .ui.data_visualizer import DataVisualizer, AsyncBackendBridge
    from .ui.pid_acquisition import PIDAcquisitionTab
    from .obd2_acquisition.core import OBD2Acquisition
    from .core.elm327_interface import ELM327Interface
    from .elm_utils import Elm327WiFi
except ImportError:
    from elm327_async import ELM327Async
    from async_json_logger import AsyncJSONLogger
    from pid_cache import PIDCache
    from obd2_async_utils import read_vin, read_pids_batch
    from heartbeat import heartbeat
    from ui.data_visualizer import DataVisualizer, AsyncBackendBridge
    from ui.pid_acquisition import PIDAcquisitionTab
    from obd2_acquisition.core import OBD2Acquisition
    from core.elm327_interface import ELM327Interface
    from elm_utils import Elm327WiFi

pid_descriptions = {
    "0C": "RPM",
    "0D": "Velocidad",
    "05": "Temp Refrigerante",
    "0F": "Temp Admisión",
    # Puedes agregar más PIDs aquí
}

# --- Agrupación de PIDs por familia/categoría ---
pid_families = {
    "Motor": [obd.commands['RPM'], obd.commands['COOLANT_TEMP'], obd.commands['INTAKE_TEMP']],
    "Velocidad": [obd.commands['SPEED']],
    "Combustible": [obd.commands['FUEL_LEVEL'], obd.commands['FUEL_PRESSURE']] if 'FUEL_LEVEL' in obd.commands else [],
    "Aire": [obd.commands['INTAKE_PRESSURE'], obd.commands['MAF']] if 'INTAKE_PRESSURE' in obd.commands else [],
    # Agrega más familias y comandos según sea necesario
}

def decode_pid(pid, response):
    import re
    bytes_data = re.findall(r'[0-9A-Fa-f]{2}', response)
    if len(bytes_data) < 4:
        return "Sin datos"
    A = int(bytes_data[2], 16)
    B = int(bytes_data[3], 16)
    pid = pid.upper()
    if pid == "0C":  # RPM
        return f"RPM: {((A * 256) + B) / 4:.0f}"
    elif pid == "0D":  # Velocidad
        return f"Velocidad: {A} km/h"
    elif pid == "05":  # Temp refrigerante
        return f"Temp Motor: {A - 40} °C"
    elif pid == "0F":  # Temp Admisión
        return f"Temp Admisión: {A - 40} °C"
    else:
        return f"Crudo: {response}"

# --- Catálogo de marcas/modelos ---
def get_makes_and_models():
    """
    Carga el catálogo de marcas/modelos desde vehicle-makes o un archivo local JSON.
    Devuelve un dict {marca: [modelos]}
    """
    catalog_path = os.path.join(os.path.dirname(__file__), '../data/vehicle_makes_models.json')
    if os.path.exists(catalog_path):
        with open(catalog_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Fallback: catálogo mínimo
    return {
        "Toyota": ["Corolla", "Hilux", "Yaris"],
        "Chevrolet": ["Sail", "Aveo", "Spark"],
        "Hyundai": ["Accent", "Elantra", "Tucson"],
        "Kia": ["Rio", "Cerato", "Sportage"],
        "Ford": ["Focus", "Fiesta", "Ranger"],
        "Nissan": ["Versa", "Sentra", "Navara"],
        "Volkswagen": ["Gol", "Polo", "Golf"],
        "Renault": ["Kwid", "Duster", "Logan"],
        "Peugeot": ["208", "2008", "308"],
        "Honda": ["Civic", "Fit", "CR-V"]
    }

# Handler global para excepciones no capturadas
import sys

def log_uncaught_exceptions(exctype, value, tb):
    import traceback
    logger.critical("Excepción no capturada:", exc_info=(exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = log_uncaught_exceptions

class OBDController:
    OBD_URL = "socket://192.168.0.10:35000"
    OBD_TIMEOUT = 1.0
    OBD_FAST = False
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.connection = None
        self.live_timer = None
        self.async_conn = None  # Para stream multipid
        self.values_layout = None  # Layout para labels multipid
        # Eliminado: NO crear ni sobrescribir tab_gauges ni layout_gauges aquí
        self.init_connections()

    def connect_obd(self):
        logger.info("Acción: conectar/desconectar OBD")
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.visualizer.set_status("Desconectado")
            self.visualizer.btn_connect.setText("Conectar")
            logger.info("OBD desconectado")
            return

        self.visualizer.set_status("Conectando…")
        try:
            self.connection = obd.OBD(self.OBD_URL, fast=self.OBD_FAST, timeout=self.OBD_TIMEOUT)
            logger.info("Intentando conectar a OBD en %s", self.OBD_URL)
        except Exception as e:
            self.visualizer.set_status("Error al conectar")
            self.visualizer.show_message("Error conexión", str(e))
            logger.error("Error al conectar OBD: %s", e, exc_info=True)
            return

        status = self.connection.status()
        logger.info("Estado de conexión OBD: %s", status)
        if status == OBDStatus.CAR_CONNECTED:
            self.visualizer.set_status("Conectado: ECU detectada")
            self.visualizer.btn_connect.setText("Desconectar")
        elif status == OBDStatus.ELM_CONNECTED:
            self.visualizer.set_status("Conectado al ELM327 (ignición apagada)")
            self.visualizer.btn_connect.setText("Desconectar")
        else:
            self.visualizer.set_status("Conexión fallida")
            self.visualizer.btn_connect.setText("Conectar")

    def leer_vin(self):
        logger.info("Acción: leer VIN")
        import obd
        from vininfo import Vin
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        # 1. Leer VIN multiframe (soporta respuesta como lista de bytes)
        resp = self.connection.query(obd.commands['VIN']) if self.connection and self.connection.is_connected() else None
        vin_obd = None
        if resp and not resp.is_null() and resp.value is not None:
            # Manejo robusto para distintos tipos de respuesta
            if hasattr(resp.value, 'raw') and resp.value.raw and isinstance(resp.value.raw, list):
                vin_bytes = b''.join(resp.value.raw)
                vin_obd = vin_bytes.decode(errors='ignore').strip('\x00').strip()
            else:
                vin_obd = str(resp.value).strip()
        logger.info(f"VIN leído por OBD: {vin_obd}")
        # 2. Mostrar decodificación parcial (país, fabricante)
        if vin_obd:
            try:
                v = Vin(vin_obd)
                decoded = f"{vin_obd} — {v.country}, {v.manufacturer}"
            except Exception as ex:
                decoded = vin_obd + " — parse parcial"
                logger.warning(f"Error decodificando VIN: {ex}")
            self.visualizer.le_vin.setText(decoded)
        else:
            self.visualizer.le_vin.setText("VIN OBD no disponible")
        # 3. Confirmación/ingreso manual del VIN
        vin_manual, ok = QInputDialog.getText(
            self.visualizer, "VIN confirmación",
            "Confirma o ingresa el VIN real del vehículo:",
            text=vin_obd or ""
        )
        logger.info(f"VIN manual ingresado: {vin_manual}, ok={ok}")
        if ok and vin_manual:
            vin_manual = vin_manual.strip()
        else:
            vin_manual = None
        # 4. Validar VIN manual (debe tener 17 caracteres alfanuméricos)
        def is_valid_vin(v):
            return v and len(v) == 17 and v.isalnum()
        use_manual = vin_manual and vin_manual != vin_obd and is_valid_vin(vin_manual)
        vin_final = vin_manual if use_manual else vin_obd
        if use_manual:
            logger.warning(f"VIN inconsistente: OBD={vin_obd}, manual={vin_manual}")
            QMessageBox.warning(
                self.visualizer, "⚠️ VIN inconsistente",
                f"VIN OBD: {vin_obd}\nVIN manual: {vin_manual}\nSe usará el VIN manual."
            )
        # 5. Si el VIN final es inválido, activar fallback manual
        if not vin_final or not is_valid_vin(vin_final):
            logger.warning("VIN inválido. Activando fallback manual.")
            QMessageBox.information(self.visualizer, "VIN no válido",
                "No se detectó un VIN válido. Habilitando selección manual.")
            self.visualizer.le_vin.setText("VIN manual requerido")
            self.visualizer.enable_vehicle_fallback(True)
            try:
                self.visualizer.create_and_connect_save_button(self.visualizer._main_layout)
            except Exception as ex:
                logger.warning(f"No se pudo agregar botón a _main_layout: {ex}")
                self.visualizer.create_and_connect_save_button(self.visualizer.tabs.currentWidget().layout())
        else:
            label = vin_final + (" (manual)" if use_manual else "")
            self.visualizer.le_vin.setText(label)
            self.visualizer.enable_vehicle_fallback(False)
            logger.info(f"VIN final usado: {label}")

    def scan_protocol(self):
        if not self.connection or not self.connection.is_connected():
            self.visualizer.le_protocol.setText("No conectado")
            return
        try:
            proto = self.connection.protocol_name()
        except Exception:
            proto = str(self.connection.status())
        self.visualizer.le_protocol.setText(proto)

    def scan_pids(self):
        if not self.connection or not self.connection.is_connected():
            self.visualizer.set_status("No conectado")
            return
        cmds = list(self.connection.supported_commands)
        self.visualizer.pid_selector.clear()
        for cmd in cmds:
            self.visualizer.pid_selector.addItem(cmd.name, cmd)
        # Poblar la lista multipid agrupada
        if hasattr(self.visualizer, 'cargar_pids_agrupados_en_lista'):
            self.visualizer.cargar_pids_agrupados_en_lista(cmds)
        self.visualizer.set_status(f"{len(cmds)} PIDs disponibles")

    def start_live(self):
        from PySide6.QtCore import QTimer
        if self.live_timer:
            self.live_timer.stop()
        self.live_timer = QTimer()
        self.live_timer.timeout.connect(self.read_selected_pid)
        self.live_timer.start(500)
        self.visualizer.set_status("Lectura en tiempo real iniciada", color="green")

    def read_selected_pid(self):
        idx = self.visualizer.pid_selector.currentIndex()
        if idx < 0 or not self.connection or not self.connection.is_connected():
            return
        cmd = self.visualizer.pid_selector.itemData(idx)
        if not cmd:
            self.visualizer.label_pid_value.setText("PID no soportado")
            return
        try:
            response = self.connection.query(cmd)
            if response.is_null():
                self.visualizer.label_pid_value.setText("Sin datos")
            else:
                self.visualizer.label_pid_value.setText(str(response.value))
        except Exception as e:
            self.visualizer.label_pid_value.setText(f"Error: {str(e)}")

    def cargar_pids_agrupados_en_lista(self, supported_cmds):
        from PySide6.QtWidgets import QListWidgetItem
        from PySide6.QtCore import Qt
        # Limpiar la lista multipid
        self.visualizer.pid_list.clear()
        # Ordenar los comandos por nombre para mejor UX
        sorted_cmds = sorted(supported_cmds, key=lambda c: c.name)
        for cmd in sorted_cmds:
            if cmd is not None:
                item = QListWidgetItem(cmd.name)
                item.setData(Qt.ItemDataRole.UserRole, cmd)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.visualizer.pid_list.addItem(item)
        self.visualizer.set_status(f"{len(sorted_cmds)} PIDs cargados en multipid")

    def to_max(self, cmd):
        # Helper para rango máximo de gauge
        return {'RPM': 8000, 'SPEED': 200, 'COOLANT_TEMP': 150, 'INTAKE_TEMP': 120, 'MAF': 200, 'THROTTLE_POS': 100, 'FUEL_LEVEL': 100, 'FUEL_PRESSURE': 800}.get(cmd.name, 100)

    def iniciar_stream_pids(self):
        logger.info("Acción: iniciar stream multipid")
        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt
        import obd
        if self.async_conn:
            self.async_conn.stop()
            self.async_conn = None
            logger.info("Stream multipid anterior detenido")
        selected_cmds = [
            self.visualizer.pid_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.visualizer.pid_list.count())
            if self.visualizer.pid_list.item(i).flags() & Qt.ItemFlag.ItemIsUserCheckable and self.visualizer.pid_list.item(i).checkState() == Qt.CheckState.Checked
        ]
        logger.info(f"PIDs seleccionados para stream multipid: {[cmd.name for cmd in selected_cmds if cmd]}")
        if not selected_cmds:
            self.visualizer.show_message("Info", "Selecciona al menos un PID")
            logger.warning("No se seleccionaron PIDs para stream multipid")
            return
        if not self.connection or not self.connection.is_connected():
            self.visualizer.show_message("Error", "No hay conexión OBD-II")
            logger.error("No hay conexión OBD-II para iniciar stream multipid")
            return
        for cmd in selected_cmds:
            if not self.connection.supports(cmd):
                logger.warning(f"PID no soportado: {cmd.name}")
        if self.values_layout is None:
            self.values_layout = self.visualizer.values_layout
        # Limpiar layout de labels
        for layout in (self.values_layout,):
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if w:
                    w.deleteLater()
        # Mostrar gauges en la pestaña Gauges
        self.visualizer.show_gauges(selected_cmds)
        # Async con delay_cmds para evitar saturación
        self.async_conn = obd.Async(
            self.OBD_URL,
            fast=self.OBD_FAST,
            timeout=self.OBD_TIMEOUT,
            delay_cmds=0.05  # Reducido para mayor frecuencia de actualización
        )
        with self.async_conn.paused():
            for cmd in selected_cmds:
                lbl = QLabel(f"{cmd.name}: --")
                self.values_layout.addWidget(lbl)
                def make_cb(c, l):
                    def cb(r):
                        val = r.value
                        logger.debug(f"PID {c.name} valor recibido: {val}")
                        if val is None or (isinstance(val, str) and (val.strip() == '' or val.strip().lower() in ['none', 'no data', 'stopped'])):
                            l.setText(f"{c.name}: Sin datos")
                            self.visualizer.update_gauge(c.name, 0)
                            logger.warning(f"PID {c.name} sin datos en stream multipid")
                        else:
                            try:
                                v = None
                                if not isinstance(val, str):
                                    try:
                                        v = float(val.magnitude)
                                    except AttributeError:
                                        pass
                                if v is None and isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], (int, float)):
                                    v = float(val[0])
                                if v is None and isinstance(val, str):
                                    import re
                                    m = re.match(r'([-+]?[0-9]*\.?[0-9]+)', val)
                                    if m:
                                        v = float(m.group(1))
                                if v is None and isinstance(val, (int, float)):
                                    v = float(val)
                                if v is not None:
                                    l.setText(f"{c.name}: {v}")
                                    self.visualizer.update_gauge(c.name, v)
                                    logger.info(f"PID {c.name} actualizado en stream multipid: {v}")
                                else:
                                    l.setText(f"{c.name}: --")
                                    self.visualizer.update_gauge(c.name, 0)
                                    logger.error(f"No se pudo extraer valor numérico de PID {c.name}: {val}")
                            except Exception as ex:
                                l.setText(f"{c.name}: --")
                                self.visualizer.update_gauge(c.name, 0)
                                logger.error(f"Error convirtiendo valor de PID {c.name}: {ex}")
                    return cb
                self.async_conn.watch(cmd, callback=make_cb(cmd, lbl), force=False)
        self.async_conn.start()
        self.visualizer.set_status("Stream multipid iniciado", color="green")
        logger.info("Stream multipid iniciado con PIDs: %s", [cmd.name for cmd in selected_cmds if cmd])

    def stop_pid_stream(self):
        if self.async_conn:
            self.async_conn.stop()
            self.async_conn = None
            self.visualizer.set_status("Stream multipid detenido", color="red")
            logger.info("Stream multipid detenido")
        self.visualizer.clear_gauges()

    def leer_dtcs(self):
        if not self.connection or not self.connection.is_connected():
            self.visualizer.dtcs_list.clear()
            self.visualizer.dtcs_list_label.setText("No conectado")
            self.visualizer.show_message("Error", "No hay conexión OBD-II")
            return
        try:
            resp = self.connection.query(obd.commands['GET_DTC'])
            if resp.is_null() or not resp.value:
                self.visualizer.dtcs_list.clear()
                self.visualizer.dtcs_list_label.setText("No se encontraron DTCs")
            else:
                self.visualizer.dtcs_list.clear()
                for code, desc in resp.value:
                    self.visualizer.dtcs_list.addItem(f"{code} – {desc or 'sin descripción'}")
                self.visualizer.dtcs_list_label.setText(f"{len(resp.value)} código(s) encontrados")
        except Exception as e:
            self.visualizer.dtcs_list.clear()
            self.visualizer.dtcs_list_label.setText("Error al leer DTCs")
            self.visualizer.show_message("Error DTC", str(e))

    def borrar_dtcs(self):
        from PySide6.QtWidgets import QMessageBox
        if not self.connection or not self.connection.is_connected():
            self.visualizer.show_message("Error", "No hay conexión OBD-II")
            return
        reply = QMessageBox.question(self.visualizer, "Confirmar borrado",
            "¿Deseas borrar todos los códigos de falla?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            resp = self.connection.query(obd.commands['CLEAR_DTC'])
            self.visualizer.dtcs_list.clear()
            self.visualizer.dtcs_list_label.setText("Códigos borrados")
            self.visualizer.show_message("Éxito", "DTCs borrados correctamente")
        except Exception as e:
            self.visualizer.show_message("Error", f"No se pudieron borrar los DTCs: {e}")

    def init_vehicle_fallback(self):
        """
        Intenta identificar el vehículo por VIN y mostrar marca/modelo/país. Si falla, aplica fallback.
        """
        catalog = get_makes_and_models()
        vin = None
        marca = modelo = pais = "Desconocido"
        # Intentar leer VIN si hay conexión
        if self.connection and self.connection.is_connected():
            resp = self.connection.query(obd.commands['VIN'])
            if not resp.is_null():
                vin = str(resp.value)
        if vin:
            try:
                info = Vin(vin)
                marca = info.manufacturer or "Desconocido"
                pais = info.country or "Desconocido"
                # Buscar modelo si posible (requiere lógica extra, aquí solo marca)
                if marca in catalog:
                    modelos = catalog[marca]
                    modelo = modelos[0] if modelos else "Desconocido"
                else:
                    modelo = "Desconocido"
            except Exception:
                marca = modelo = pais = "Desconocido"
        else:
            # Fallback: sugerir selección manual o mostrar desconocido
            marca = modelo = pais = "Desconocido"
        # Actualizar UI si existen los campos
        if hasattr(self.visualizer, 'le_marca'):
            self.visualizer.le_marca.setText(marca)
        if hasattr(self.visualizer, 'le_modelo'):
            self.visualizer.le_modelo.setText(modelo)
        if hasattr(self.visualizer, 'le_pais'):
            self.visualizer.le_pais.setText(pais)
        if hasattr(self.visualizer, 'set_status'):
            self.visualizer.set_status(f"Vehículo: {marca} {modelo} ({pais})")

    def init_connections(self):
        self.visualizer.btn_connect.clicked.connect(self.connect_obd)
        self.visualizer.btn_scan_pids.clicked.connect(self.scan_pids)
        self.visualizer.btn_start_live.clicked.connect(self.start_live)
        if hasattr(self.visualizer, 'btn_read_vin'):
            self.visualizer.btn_read_vin.clicked.connect(self.leer_vin)
        if hasattr(self.visualizer, 'btn_scan_protocols'):
            self.visualizer.btn_scan_protocols.clicked.connect(self.scan_protocol)
        # CORRECCIÓN: conectar btn_start_stream al método correcto de OBDController
        if hasattr(self.visualizer, 'btn_start_stream'):
            try:
                self.visualizer.btn_start_stream.clicked.disconnect()
            except Exception:
                pass
            self.visualizer.btn_start_stream.clicked.connect(self.iniciar_stream_pids)
        if hasattr(self.visualizer, 'btn_read_dtcs'):
            self.visualizer.btn_read_dtcs.clicked.connect(self.leer_dtcs)
        if hasattr(self.visualizer, 'btn_clear_dtcs'):
            self.visualizer.btn_clear_dtcs.clicked.connect(self.borrar_dtcs)
        # Eliminar conexión redundante que detenía el stream al salir de multipid
        # if hasattr(self.visualizer, 'tabs'):
        #     self.visualizer.tabs.currentChanged.connect(lambda idx: self.stop_pid_stream() if idx != self.visualizer.tabs.indexOf(self.visualizer.tab_pids) else None)
        self.init_vehicle_fallback()

if __name__ == "__main__":
    logger.info("Iniciando aplicación OBD2 Scanner...")
    from obd2_acquisition.core import OBD2Acquisition
    import asyncio
    from qasync import QEventLoop
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    OBD_PORT = "socket://192.168.0.10:35000"
    backend = OBD2Acquisition(port=OBD_PORT)
    win = DataVisualizer(lambda: {}, pid_manager=None, elm327=None, parse_pid_response=None, backend=backend)
    controller = OBDController(win)
    win.cargar_pids_agrupados_en_lista = controller.cargar_pids_agrupados_en_lista
    win.stop_pid_stream = controller.stop_pid_stream
    def launch_tuning_loop(session_id, map_version, pid_values_dict):
        vin = win.le_vin.text() or ""
        make = win.vehicle_info.get('make', 'default')
        model = win.vehicle_info.get('model', 'default')
        async def _run():
            if not backend.connected:
                try:
                    await backend.connect()
                except Exception as ex:
                    logger.error(f"Error conectando backend OBD2Acquisition: {ex}")
                    return
            await backend.read_tuning_loop(vin, make, model)
        asyncio.create_task(_run())
    win.tuning_widget.tuning_update.connect(launch_tuning_loop)
    old_close = win.closeEvent
    def new_close(a0):
        logger.info("Cerrando aplicación OBD2 Scanner...")
        controller.stop_pid_stream()
        if hasattr(backend, 'disconnect'):
            try:
                asyncio.create_task(backend.disconnect())
            except Exception:
                pass
        old_close(a0)
    win.closeEvent = new_close
    win.show()
    logger.info("Ventana principal mostrada. Esperando eventos Qt+asyncio...")
    print("[DEBUG] Ventana principal mostrada. Esperando eventos Qt+asyncio...")
    with loop:
        sys.exit(loop.run_forever())
