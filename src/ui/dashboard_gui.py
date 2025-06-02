"""
Dashboard OBD-II Multiplataforma – PyQt6
----------------------------------------
Interfaz gráfica profesional para monitoreo, logging y diagnóstico OBD-II en tiempo real.
Cumple los más altos estándares de UI/UX, robustez y modularidad.
"""

import sys
import traceback
import time
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QCheckBox, QScrollArea, QWidget, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from src.ui.widgets.gauge import GaugeWidget
from src.obd.connection import OBDConnection
from src.obd.elm327 import ELM327
from src.obd.pids import PIDS
from src.obd.pids_ext import PIDS as PIDS_EXT
from src.storage.export import export_dynamic_log
from src.utils.logging_app import log_evento_app

# --- Corrección: Conversión robusta de datos OBD-II a int/float en modo real ---
# Todos los valores numéricos de PIDs se convierten a int/float antes de operar, loguear o exportar.
# Si la conversión falla, se deja el valor original y se puede advertir en el log o UI.

# --- MOCK: Abstracción de fuente de datos (real/emulador) ---
class OBDDataSource:
    def __init__(self, modo='emulador'):
        print(f'[DEBUG] OBDDataSource.__init__: modo={modo}')
        self.modo = modo
        self.escenario = 'ralenti'  # Escenario activo para emulador
        self.rpm = 800
        self.vel = 0
        self.dtc = []
        self.connected = False
        self.conn = None
        self.elm = None
        self.log = []  # Lista para logging en memoria
        self.db_conn = None
        self.db_cursor = None
        print(f'[DEBUG] OBDDataSource inicializado en modo: {self.modo}')

    def set_escenario(self, escenario):
        self.escenario = escenario
        log_evento_app('INFO', f'Escenario cambiado a: {escenario}', contexto='set_escenario')

    def connect(self):
        try:
            if self.modo == 'real':
                try:
                    self.conn = OBDConnection(mode='wifi', ip='192.168.0.10', tcp_port=35000)
                    self.conn.connect()
                    self.elm = ELM327(self.conn)
                    self.elm.initialize()
                    self.connected = True
                    log_evento_app('INFO', 'Conexión OBD-II exitosa', contexto='connect')
                except Exception as e:
                    self.connected = False
                    log_evento_app('ERROR', f'Fallo de conexión OBD-II: {e}', contexto='connect')
                    raise e
            else:
                self.connected = True
                log_evento_app('INFO', 'Modo emulador conectado', contexto='connect')
            # Conexión a SQLite para logging persistente
            self.db_conn = sqlite3.connect('obd_log.db')
            self.db_cursor = self.db_conn.cursor()
            self.db_cursor.execute('''CREATE TABLE IF NOT EXISTS lecturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                rpm INTEGER,
                vel INTEGER,
                escenario TEXT
            )''')
            self.db_conn.commit()
        except Exception as e:
            log_evento_app('ERROR', f'Error general en connect: {e}', contexto='connect')
            raise e

    def disconnect(self):
        if self.modo == 'real' and self.conn:
            try:
                self.conn.close()
                log_evento_app('INFO', 'Desconexión OBD-II exitosa', contexto='disconnect')
            except Exception as e:
                log_evento_app('ERROR', f'Error al cerrar conexión: {e}', contexto='disconnect')
        self.connected = False
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None
            self.db_cursor = None
            log_evento_app('INFO', 'Base de datos cerrada', contexto='disconnect')

    def safe_cast(self, val):
        try:
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return val
            if isinstance(val, str):
                if '.' in val:
                    return float(val)
                return int(val)
        except (ValueError, TypeError) as e:
            log_evento_app('ADVERTENCIA', f'Conversión fallida: {val} ({e})', contexto='safe_cast')
            return val
        return val

    def read_data(self, pids=None):
        print(f'[DEBUG] Entrando a read_data, modo: {self.modo.upper()}')
        from src.obd.emulador import emular_datos_obd2
        # Recibe los PIDs desde la UI (DashboardOBD) siempre por parámetro
        if not self.connected:
            print('[DEBUG] read_data: No conectado')
            return {pid: None for pid in (pids or ['rpm', 'vel'])}
        data = {}
        pids_legibles = [pid for pid in (pids or ['rpm', 'vel']) if pid in PIDS_EXT or pid in ['rpm', 'vel']]
        if 'escenario' not in pids_legibles:
            pids_legibles.append('escenario')
        print(f'[DEBUG] read_data: modo={self.modo}, pids_legibles={pids_legibles}, escenario={self.escenario}')
        try:
            log_evento_app('INFO', f'[DASHBOARD] PIDs seleccionados antes de emular: {pids_legibles}', contexto='read_data')
        except Exception:
            pass
        if self.modo == 'emulador':
            escenarios = [{'fase': self.escenario, 'duracion': 1}]
            datos = emular_datos_obd2(escenarios=escenarios, pids=pids_legibles, registros_por_fase=1)
            data = datos[0]
            for k, v in data.items():
                if k not in ['timestamp', 'escenario']:
                    data[k] = self.safe_cast(v)
            print(f'[DEBUG] read_data: datos emulados={data}')
        elif self.modo == 'real' and self.elm:
            for pid in pids_legibles:
                if pid in PIDS:
                    resp = self.elm.send_pid(PIDS[pid]['cmd'])
                    data[pid] = self.safe_cast(resp)
                    print(f'[DEBUG] read_data: pid={pid}, resp={resp}, cast={data[pid]}')
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        data['timestamp'] = ts
        # Loguear todos los PIDs seleccionados, no solo rpm/vel
        if any(self.safe_cast(data.get(pid)) not in (None, '', 'None') for pid in pids_legibles if pid not in ['timestamp', 'escenario']):
            self.log.append({pid: data.get(pid, '') for pid in (['timestamp'] + pids_legibles)})
            print(f'[DEBUG] read_data: registro loggeado: {self.log[-1]}')
        else:
            print(f"[ADVERTENCIA] Registro omitido por datos vacíos: {data}")
        return data

    def get_log(self):
        # Devuelve el log en memoria
        return self.log

    def get_log_db(self):
        # Devuelve el log desde SQLite
        if self.db_conn and self.db_cursor:
            try:
                self.db_cursor.execute('SELECT timestamp, rpm, vel, escenario FROM lecturas ORDER BY id')
                return self.db_cursor.fetchall()
            except Exception as e:
                log_evento_app('ERROR', f'Error al leer log de BD: {e}', contexto='get_log_db')
                return []
        return []

class DashboardOBD(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Dashboard OBD-II Multiplataforma')
        self.setGeometry(100, 100, 900, 500)
        self.setStyleSheet('background-color: #181c20; color: #f0f0f0;')
        self.data_source = OBDDataSource('emulador')
        self.selected_pids = list(PIDS_EXT.keys())[:2]  # Por defecto RPM y Velocidad
        self.pid_checkboxes = {}
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)  # Refresco más rápido (100 ms)

    def init_ui(self):
        layout = QVBoxLayout()
        # Selector de fuente de datos
        fuente_layout = QHBoxLayout()
        fuente_label = QLabel('Fuente de datos:')
        fuente_label.setFont(QFont('Arial', 12))
        self.fuente_combo = QComboBox()
        self.fuente_combo.addItems(['Emulador', 'Vehículo real'])
        self.fuente_combo.currentIndexChanged.connect(self.cambiar_fuente)
        fuente_layout.addWidget(fuente_label)
        fuente_layout.addWidget(self.fuente_combo)
        fuente_layout.addStretch()
        self.btn_conectar = QPushButton('Conectar')
        self.btn_conectar.clicked.connect(self.conectar_fuente)
        self.btn_conectar.setStyleSheet('background-color: #2e8b57; color: white; font-weight: bold;')
        self.btn_desconectar = QPushButton('Desconectar')
        self.btn_desconectar.clicked.connect(self.desconectar_fuente)
        self.btn_desconectar.setStyleSheet('background-color: #b22222; color: white; font-weight: bold;')
        fuente_layout.addWidget(self.btn_conectar)
        fuente_layout.addWidget(self.btn_desconectar)
        layout.addLayout(fuente_layout)
        # Gauges dinámicos
        self.gauges_layout = QHBoxLayout()
        self.gauge_widgets = {}
        # Siempre activos por defecto
        self.gauge_rpm = GaugeWidget(0, 8000, 'RPM', QColor(0, 200, 255))
        self.gauge_vel = GaugeWidget(0, 240, 'km/h', QColor(255, 120, 0))
        self.gauges_layout.addWidget(self.gauge_rpm)
        self.gauges_layout.addWidget(self.gauge_vel)
        self.gauge_widgets['rpm'] = self.gauge_rpm
        self.gauge_widgets['vel'] = self.gauge_vel
        layout.addLayout(self.gauges_layout)
        # Panel DTC
        dtc_layout = QHBoxLayout()
        self.dtc_label = QLabel('DTC: ---')
        self.dtc_label.setFont(QFont('Arial', 14))
        self.btn_leer_dtc = QPushButton('Leer DTC')
        self.btn_leer_dtc.clicked.connect(self.leer_dtc)
        self.btn_borrar_dtc = QPushButton('Borrar DTC')
        self.btn_borrar_dtc.clicked.connect(self.borrar_dtc)
        dtc_layout.addWidget(self.dtc_label)
        dtc_layout.addWidget(self.btn_leer_dtc)
        dtc_layout.addWidget(self.btn_borrar_dtc)
        layout.addLayout(dtc_layout)
        # Panel de logs y exportación
        log_layout = QHBoxLayout()
        self.btn_exportar = QPushButton('Exportar Log')
        self.btn_exportar.clicked.connect(self.exportar_log)
        log_layout.addWidget(self.btn_exportar)
        layout.addLayout(log_layout)
        # Tabla de log en tiempo real
        self.table_log = QTableWidget(0, len(self.selected_pids) + 2)
        headers = ['Timestamp'] + [PIDS_EXT[pid]['desc'] if pid in PIDS_EXT else pid for pid in self.selected_pids] + ['Escenario']
        self.table_log.setHorizontalHeaderLabels(headers)
        self.table_log.setStyleSheet('background-color: #23272e; color: #f0f0f0;')
        self.table_log.setMinimumHeight(180)
        layout.addWidget(self.table_log)
        # Panel de selección dinámica de PIDs
        pid_panel = QVBoxLayout()
        pid_label = QLabel('Selecciona hasta 8 parámetros a monitorear:')
        pid_label.setFont(QFont('Arial', 12))
        pid_panel.addWidget(pid_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        pid_widget = QWidget()
        grid = QGridLayout()
        self.pid_checkboxes = {}
        # Checkboxes para todos los PIDs
        for i, (pid, info) in enumerate(PIDS_EXT.items()):
            cb = QCheckBox(f"{pid} - {info.get('desc', pid)}")
            if pid in ['rpm', 'vel']:
                cb.setChecked(True)
            cb.stateChanged.connect(self.on_pid_selection_changed)
            self.pid_checkboxes[pid] = cb
            grid.addWidget(cb, i // 2, i % 2)
        # Checkboxes para quitar gauges fijos
        self.cb_rpm = QCheckBox('Quitar gauge RPM')
        self.cb_rpm.stateChanged.connect(self.on_pid_selection_changed)
        grid.addWidget(self.cb_rpm, len(PIDS_EXT) // 2 + 1, 0)
        self.cb_vel = QCheckBox('Quitar gauge Velocidad')
        self.cb_vel.stateChanged.connect(self.on_pid_selection_changed)
        grid.addWidget(self.cb_vel, len(PIDS_EXT) // 2 + 1, 1)
        pid_widget.setLayout(grid)
        scroll.setWidget(pid_widget)
        pid_panel.addWidget(scroll)
        layout.addLayout(pid_panel)
        # Panel de selección de modo de emulación (solo visible en modo emulador)
        self.modo_label = QLabel('Modo de emulación:')
        self.modo_label.setFont(QFont('Arial', 12))
        self.modo_combo = QComboBox()
        self.modo_combo.addItems(['ralenti', 'aceleracion', 'crucero', 'frenado', 'ciudad', 'carretera', 'falla'])
        self.modo_combo.setCurrentText('ralenti')
        self.modo_combo.currentTextChanged.connect(self.on_modo_changed)
        # Solo mostrar si la fuente es emulador
        if hasattr(self.data_source, 'modo') and self.data_source.modo == 'emulador':
            layout.addWidget(self.modo_label)
            layout.addWidget(self.modo_combo)
        # Mensajes y estado
        self.status_label = QLabel('Desconectado.')
        self.status_label.setFont(QFont('Arial', 10))
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def cambiar_fuente(self):
        modo = 'emulador' if self.fuente_combo.currentIndex() == 0 else 'real'
        print(f'[DEBUG] cambiar_fuente: Seleccionado modo {modo.upper()}')
        self.data_source = OBDDataSource(modo)
        self.status_label.setText(f'Fuente cambiada a: {modo}')

    def check_wifi_obdii_connection(self, ip, port, timeout=3):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, port))
            s.close()
            return True, ''
        except Exception as e:
            return False, str(e)

    def conectar_fuente(self):
        try:
            print('[DEBUG] conectar_fuente: Iniciando conexión de fuente')
            self.data_source.disconnect()
            idx = self.fuente_combo.currentIndex()
            modo = 'emulador' if idx == 0 else 'real'
            print(f'[DEBUG] conectar_fuente: Seleccionado modo {modo.upper()}')
            self.data_source = OBDDataSource(modo)
            if modo == 'real':
                ip = '192.168.0.10'  # Ajustar si es configurable
                puerto = 35000
                ok, error = self.check_wifi_obdii_connection(ip, puerto)
                if not ok:
                    print(f'[DEBUG] conectar_fuente: Error de conexión WiFi: {error}')
                    self.status_label.setText(
                        'Sin conexión con el OBD-II por WiFi. Revisa la red y reinicia el adaptador.\nDetalle: ' + error)
                    return
            self.data_source.connect()
            print(f'[DEBUG] conectar_fuente: Conectado={self.data_source.connected}')
            if self.data_source.connected:
                self.status_label.setText(f'Conectado a: {modo}')
            else:
                self.status_label.setText('No conectado.')
        except Exception as e:
            self.status_label.setText(f'Error al conectar: {e}')
            print(f"[OBD-II WIFI] Error crítico: {e}")

    def desconectar_fuente(self):
        try:
            self.data_source.disconnect()
            self.status_label.setText('Desconectado.')
        except Exception as e:
            self.status_label.setText(f'Error al desconectar: {e}')

    def on_pid_selection_changed(self):
        # Siempre activos rpm y vel salvo que se marque quitar
        seleccionados = [pid for pid, cb in self.pid_checkboxes.items() if cb.isChecked()]
        if not self.cb_rpm.isChecked() and 'rpm' not in seleccionados:
            seleccionados.append('rpm')
        if not self.cb_vel.isChecked() and 'vel' not in seleccionados:
            seleccionados.append('vel')
        if self.cb_rpm.isChecked() and 'rpm' in seleccionados:
            seleccionados.remove('rpm')
        if self.cb_vel.isChecked() and 'vel' in seleccionados:
            seleccionados.remove('vel')
        if len(seleccionados) > 8:
            for pid in seleccionados[8:]:
                if pid in self.pid_checkboxes:
                    self.pid_checkboxes[pid].setChecked(False)
            seleccionados = seleccionados[:8]
        self.selected_pids = seleccionados
        # Actualizar gauges dinámicos
        for pid, gauge in list(self.gauge_widgets.items()):
            if pid not in self.selected_pids and pid not in ['rpm', 'vel']:
                self.gauges_layout.removeWidget(gauge)
                gauge.deleteLater()
                del self.gauge_widgets[pid]
        for pid in self.selected_pids:
            if pid not in self.gauge_widgets and pid in PIDS_EXT and pid not in ['rpm', 'vel']:
                minv = PIDS_EXT[pid].get('min', 0)
                maxv = PIDS_EXT[pid].get('max', 100)
                label = PIDS_EXT[pid].get('desc', pid)
                color = QColor(120, 255, 120)
                gauge = GaugeWidget(minv, maxv, label, color)
                self.gauges_layout.addWidget(gauge)
                self.gauge_widgets[pid] = gauge
        # Mostrar/ocultar gauges fijos
        self.gauge_rpm.setVisible(not self.cb_rpm.isChecked())
        self.gauge_vel.setVisible(not self.cb_vel.isChecked())
        self.status_label.setText(f"PIDs seleccionados: {', '.join(self.selected_pids)}")

    def on_modo_changed(self, modo):
        # Cambia el escenario de emulación en la fuente de datos
        if hasattr(self.data_source, 'set_escenario'):
            self.data_source.set_escenario(modo)
        self.status_label.setText(f"Modo de emulación: {modo}")

    def update_data(self):
        try:
            print(f'[DEBUG] update_data: selected_pids={self.selected_pids}')
            print(f'[DEBUG] update_data: modo activo={self.data_source.modo}')
            data = self.data_source.read_data(self.selected_pids)
            print(f'[DEBUG] update_data: data={data}')
            # Actualizar gauges fijos
            if data.get('rpm') not in (None, '', 'None'):
                self.gauge_widgets['rpm'].setValue(data.get('rpm', 0))
            else:
                self.gauge_widgets['rpm'].setValue(0)
                msg = 'Sin datos de RPM'
                self.status_label.setText(msg)
                log_evento_app('ADVERTENCIA', msg, contexto='update_data')
            if data.get('vel') not in (None, '', 'None'):
                self.gauge_widgets['vel'].setValue(data.get('vel', 0))
            else:
                self.gauge_widgets['vel'].setValue(0)
                msg = 'Sin datos de velocidad'
                self.status_label.setText(msg)
                log_evento_app('ADVERTENCIA', msg, contexto='update_data')
            # Actualiza gauges dinámicos
            for pid, gauge in self.gauge_widgets.items():
                if pid not in ['rpm', 'vel']:
                    if data.get(pid) not in (None, '', 'None'):
                        gauge.setValue(data.get(pid, 0))
                    else:
                        gauge.setValue(0)
                        msg = f'Sin datos de {pid}'
                        self.status_label.setText(msg)
                        log_evento_app('ADVERTENCIA', msg, contexto='update_data')
            # Actualiza tabla de log dinámica
            log = self.data_source.get_log()[-100:]
            print(f'[DEBUG] update_data: log[-5:]={log[-5:]}')
            self.table_log.setColumnCount(len(self.selected_pids) + 2)
            headers = ['Timestamp'] + [PIDS_EXT[pid]['desc'] if pid in PIDS_EXT else pid for pid in self.selected_pids] + ['Escenario']
            self.table_log.setHorizontalHeaderLabels(headers)
            self.table_log.setRowCount(len(log))
            for i, row in enumerate(log):
                self.table_log.setItem(i, 0, QTableWidgetItem(row.get('timestamp', '')))
                for j, pid in enumerate(self.selected_pids):
                    self.table_log.setItem(i, j+1, QTableWidgetItem(str(row.get(pid, ''))))
                self.table_log.setItem(i, len(self.selected_pids)+1, QTableWidgetItem(row.get('escenario', '')))
        except Exception as e:
            msg = f'Error: {e}'
            self.status_label.setText(msg)
            log_evento_app('ERROR', msg, contexto='update_data')
            traceback.print_exc()

    def leer_dtc(self):
        try:
            dtc = self.data_source.get_dtc()
            self.dtc_label.setText(f'DTC: {dtc if dtc else "---"}')
            self.status_label.setText('Lectura de DTC exitosa.')
        except Exception as e:
            self.status_label.setText(f'Error al leer DTC: {e}')

    def borrar_dtc(self):
        try:
            self.data_source.clear_dtc()
            self.dtc_label.setText('DTC: ---')
            self.status_label.setText('DTC borrados.')
        except Exception as e:
            self.status_label.setText(f'Error al borrar DTC: {e}')

    def exportar_log(self):
        try:
            fname, _ = QFileDialog.getSaveFileName(self, 'Exportar Log', '', 'CSV (*.csv)')
            if fname:
                # Obtiene los datos y los PIDs activos del log en memoria
                log = self.data_source.get_log()
                pids = ['timestamp'] + self.selected_pids
                from src.storage.export import export_dynamic_log
                valido, errores = export_dynamic_log(fname, log, pids)
                if valido:
                    self.status_label.setText('Log guardado correctamente. El archivo es válido y cumple con los estándares.')
                else:
                    self.status_label.setText(f"Atención: El log presenta errores: {errores}")
        except Exception as e:
            self.status_label.setText(f'Error al exportar: {e}')

def main():
    app = QApplication(sys.argv)
    win = DashboardOBD()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
