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

# --- INTEGRACIÓN DE MÓDULO DTC MANAGER ---
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from diagnostico import dtc_manager

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
        # self.init_connections()  # Eliminado: no existe este método

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
            # El método create_and_connect_save_button ya no existe ni es necesario.
            # El fallback manual de VIN ahora se activa solo con enable_vehicle_fallback(True).
            self.visualizer.enable_vehicle_fallback(True)
            logger.info("Fallback manual de VIN activado correctamente.")
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
        # Mostrar gauges en la pestaña Gauges (el método show_gauges no existe en visualizer, así que se omite)
        # self.visualizer.show_gauges(selected_cmds)
        # En su lugar, los valores se mostrarán en el layout multipid (values_layout)
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
                                    logger.info(f"PID {c.name} actualizado en stream multipid: {v}")
                                else:
                                    l.setText(f"{c.name}: --")
                                    logger.error(f"No se pudo extraer valor numérico de PID {c.name}: {val}")
                            except Exception as ex:
                                l.setText(f"{c.name}: --")
                                logger.error(f"Error convirtiendo valor de PID {c.name}: {ex}")
                # Registrar callback en el objeto cmd para evitar cierre prematuro de variables
                cmd._callback = make_cb(cmd, lbl)
                # Iniciar el stream para cada PID seleccionado
                self.async_conn.watch(cmd, cmd._callback)
        # Iniciar conexión asíncrona
        self.async_conn.start()
        logger.info("Stream multipid iniciado correctamente")

    def detener_stream_pids(self):
        logger.info("Acción: detener stream multipid")
        if self.async_conn:
            self.async_conn.stop()
            self.async_conn = None
            logger.info("Stream multipid detenido")
        else:
            logger.warning("No hay stream multipid activo para detener")

    def leer_dtc(self):
        logger.info("Acción: leer DTCs")
        if not self.connection or not self.connection.is_connected():
            self.visualizer.set_status("No conectado")
            return
        try:
            # Usar el dtc_manager funcional
            dtcs = dtc_manager.leer_dtc()
            logger.info(f"DTCs leídos: {dtcs}")
            if dtcs and len(dtcs) > 0 and dtcs[0].get("codigo"):
                self.visualizer.mostrar_dtcs(dtcs)
                self.visualizer.set_status(f"{len(dtcs)} DTCs encontrados")
            else:
                self.visualizer.set_status(dtcs[0]["descripcion"] if dtcs else "Sin DTCs")
        except Exception as e:
            logger.error(f"Error leyendo DTCs: {e}", exc_info=True)
            self.visualizer.set_status("Error al leer DTCs")
            self.visualizer.show_message("Error DTC", str(e))

    # Alias para compatibilidad con la GUI
    def leer_dtcs(self):
        return self.leer_dtc()

    def borrar_dtcs(self):
        logger.info("Acción: borrar DTCs")
        if not self.connection or not self.connection.is_connected():
            self.visualizer.set_status("No conectado")
            return
        try:
            res = dtc_manager.borrar_dtc()
            logger.info(f"Resultado borrar DTCs: {res}")
            if res.get("exito"):
                self.visualizer.set_status("DTCs borrados")
                self.visualizer.show_message("Éxito", "DTCs borrados correctamente")
            else:
                self.visualizer.set_status("Error al borrar DTCs")
                self.visualizer.show_message("Error", res.get("mensaje", "No se pudieron borrar los DTCs"))
        except Exception as e:
            logger.error(f"Error borrando DTCs: {e}", exc_info=True)
            self.visualizer.set_status("Error al borrar DTCs")
            self.visualizer.show_message("Error", str(e))

    def seleccionar_vehiculo(self, make, model):
        logger.info(f"Acción: seleccionar vehículo {make} {model}")
        # 1. Actualizar campos de VIN, marca y modelo
        self.visualizer.le_vin.setText("VIN manual requerido")
        self.visualizer.le_make.setText(make)
        self.visualizer.le_model.setText(model)
        # 2. Deshabilitar entrada de VIN y mostrar mensaje
        self.visualizer.le_vin.setEnabled(False)
        self.visualizer.set_status(f"Vehículo {make} {model} seleccionado")
        # 3. Habilitar botón de conexión
        self.visualizer.btn_connect.setEnabled(True)
        # 4. Guardar configuración de vehículo
        self.guardar_configuracion_vehiculo(make, model)

    def guardar_configuracion_vehiculo(self, make, model):
        logger.info(f"Guardar configuración de vehículo: {make} {model}")
        # Aquí se puede implementar la lógica para guardar la configuración del vehículo
        # Por ejemplo, guardar en un archivo JSON o en la base de datos
        pass

    def cargar_configuracion_vehiculo(self):
        logger.info("Cargar configuración de vehículo")
        # Aquí se puede implementar la lógica para cargar la configuración del vehículo
        # Por ejemplo, leer de un archivo JSON o de la base de datos
        # y actualizar los campos de marca, modelo y VIN en la interfaz
        pass

    def activar_debug(self, activar):
        logger.info(f"Activar debug: {activar}")
        if activar:
            logging.getLogger("OBD2App").setLevel(logging.DEBUG)
            self.visualizer.set_status("Modo debug activado")
        else:
            logging.getLogger("OBD2App").setLevel(logging.INFO)
            self.visualizer.set_status("Modo debug desactivado")

    def reiniciar(self):
        logger.info("Reiniciar aplicación")
        # Aquí se puede implementar la lógica para reiniciar la aplicación
        # Por ejemplo, reiniciar el bucle de eventos o volver a cargar módulos
        pass

    def cerrar(self):
        logger.info("Cerrar aplicación")
        # Aquí se puede implementar la lógica para cerrar la aplicación
        # Por ejemplo, guardar configuración, cerrar conexiones, etc.
        pass

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    visualizer = DataVisualizer(get_data_fn=lambda: {})  # Puedes reemplazar get_data_fn por tu función real
    controller = OBDController(visualizer)
    visualizer.set_controller(controller)
    visualizer.show()
    sys.exit(app.exec())
