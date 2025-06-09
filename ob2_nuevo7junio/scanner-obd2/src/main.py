"""
main.py - Entrada principal del Scanner OBD2
"""
from core.elm327_interface import ELM327Interface
from core.logger import get_logger
from core.pid_manager import PIDManager
from ui.data_visualizer import DataVisualizer
from PyQt6.QtWidgets import QApplication, QInputDialog
from PyQt6.QtCore import QThread, pyqtSignal
from collections import deque
import os
import time
import re
import sys
import threading

# --- Clase para adquisición asíncrona de datos ---
class DataAcquisitionThread(QThread):
    data_updated = pyqtSignal(dict)
    pid_disabled = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, elm, pid_manager, get_selected_pids_fn, parse_pid_response, parent=None):
        super().__init__(parent)
        self.elm = elm
        self.pid_manager = pid_manager
        self.get_selected_pids_fn = get_selected_pids_fn
        self.parse_pid_response = parse_pid_response
        self.running = True
        self.error_counts = {}
        from core.logger import get_logger
        self.logger = get_logger()
        # Buffers circulares para suavizado (ahora para todos los PIDs)
        self.buffers = {}
        self.buffer_len = 8  # Puedes ajustar el tamaño del suavizado

    def run(self):
        import time
        last_emit = time.time()
        while self.running:
            data = {}
            pids = self.get_selected_pids_fn()
            for pid in pids:
                info = self.pid_manager.get_pid_info(pid)
                if not info:
                    continue
                try:
                    resp = self.elm.send_command(pid)
                    if any(x in resp for x in ["NO DATA", "STOPPED", "?"]):
                        self.error_counts[pid] = self.error_counts.get(pid, 0) + 1
                        if self.error_counts[pid] >= 3:
                            self.pid_disabled.emit(pid)
                            continue
                    else:
                        self.error_counts[pid] = 0
                    value = self.parse_pid_response(resp, info.get('formula', 'A'))
                    # Suavizado: aplicar a todos los PIDs
                    try:
                        val_float = float(str(value).split()[0])
                    except Exception:
                        val_float = 0
                    if pid not in self.buffers:
                        from collections import deque
                        self.buffers[pid] = deque(maxlen=self.buffer_len)
                    self.buffers[pid].append(val_float)
                    smoothed = sum(self.buffers[pid]) / len(self.buffers[pid])
                    data[pid] = f"{round(smoothed, 2)} {info['unit']}"
                except Exception as e:
                    self.logger.error(f"Error leyendo PID {pid}: {e}")
                    self.error_counts[pid] = self.error_counts.get(pid, 0) + 1
                    if self.error_counts[pid] >= 3:
                        self.pid_disabled.emit(pid)
            # Emitir solo si hay cambios o cada 0.5s
            now = time.time()
            if data and (now - last_emit > 0.15):
                self.data_updated.emit(data)
                last_emit = now
            self.msleep(80)  # Reduce el tiempo de espera para mayor fluidez

    def stop(self):
        self.running = False
        self.wait()

def main():
    logger = get_logger()
    logger.info("Iniciando Scanner OBD2...")
    app = QApplication(sys.argv)
    # Diálogo para elegir modo demo/real
    modo, ok = QInputDialog.getItem(None, "Modo de conexión", "¿Deseas ejecutar en modo demo/emulador o real?", ["Demo/Emulador", "Real"], 0, False)
    if not ok:
        sys.exit(0)
    use_emulador = (modo == "Demo/Emulador")
    pid_path = os.path.join(os.path.dirname(__file__), "..", "data", "pid_definitions.json")
    pid_manager = PIDManager(pid_path)
    logger.info(f"PIDs disponibles: {len(pid_manager.list_all_pids())}")
    elm = ELM327Interface(mode="emulador" if use_emulador else "real")
    if not elm.connect():
        logger.error("No se pudo conectar con ELM327.")
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error de conexión")
        msg.setText("No se pudo conectar con el dispositivo ELM327.\n\nVerifica la conexión y vuelve a intentarlo.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return
    logger.info(f"Conexión ELM327 {'emulador' if use_emulador else 'real'} exitosa.")
    response = elm.send_command("0100")
    logger.info(f"Respuesta a 0100: {response.strip()}")
    def parse_supported_pids(resp):
        try:
            parts = resp.replace('\r', ' ').replace('\n', ' ').split()
            idx = parts.index("41") if "41" in parts else -1
            if idx != -1 and len(parts) > idx+5:
                supported = int("".join(parts[idx+2:idx+6]), 16)
                base = 0x00
                result = []
                for i in range(32):
                    if supported & (1 << (31-i)):
                        pid = f"01{base+i:02X}"
                        result.append(pid)
                return result
        except Exception as e:
            logger.error(f"Error decodificando PIDs soportados: {e}")
        return []
    supported_pids = parse_supported_pids(response)
    logger.info(f"PIDs soportados detectados: {supported_pids}")
    if not supported_pids:
        logger.warning("No se detectaron PIDs soportados. Usando ejemplo por defecto.")
        supported_pids = ["010C", "010D", "0105"]
    def parse_pid_response(resp: str, formula: str) -> str:
        try:
            bytes_hex = re.findall(r"[0-9A-Fa-f]{2}", resp)
            if len(bytes_hex) < 3:
                return "No data"
            data_bytes = bytes_hex[2:]
            vals = {}
            for idx, var in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
                if idx < len(data_bytes):
                    try:
                        vals[var] = int(data_bytes[idx], 16)
                    except Exception:
                        vals[var] = 0  # Valor por defecto si hay error de conversión
            # Validar que la fórmula solo use variables válidas y que los valores sean numéricos
            safe_vals = {k: (v if isinstance(v, (int, float)) else 0) for k, v in vals.items()}
            try:
                result = eval(formula, {}, safe_vals)
            except Exception as e:
                return f"Parse error: {e}"
            # Asegurar que el resultado sea numérico antes de redondear
            if isinstance(result, (int, float)):
                return str(round(result, 2))
            else:
                return str(result)
        except Exception as e:
            return f"Parse error: {e}"
    win = DataVisualizer(lambda: {}, pid_manager=pid_manager, elm327=elm)
    # --- Integración asíncrona ---
    def get_selected_pids():
        return list(win.selected_pids) if hasattr(win, 'selected_pids') and win.selected_pids else list(pid_manager.get_all_pid_info().keys())
    data_thread = DataAcquisitionThread(elm, pid_manager, get_selected_pids, parse_pid_response)
    def update_data(data):
        if hasattr(win, 'update_data'):
            win.update_data(data)
    def disable_pid(pid):
        if hasattr(win, 'disable_pid'):
            win.disable_pid(pid)
    data_thread.data_updated.connect(update_data)
    data_thread.pid_disabled.connect(disable_pid)
    data_thread.start()
    win.show()
    app.exec()
    data_thread.stop()
    elm.close()
    logger.info("Sesión finalizada.")

if __name__ == "__main__":
    main()
