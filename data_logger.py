import os
import csv
import logging
import sqlite3
from datetime import datetime

class DataLogger:
    """Clase para el registro de datos OBD (CSV y SQLite)"""
    def __init__(self):
        self.log_dir = "logs"
        self.log_file = None
        self.sqlite_file = None
        self.active = False
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        self.sqlite_conn = None
        self.sqlite_enabled = False

    def _setup_logging(self):
        """Configura el directorio de logs"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def start_logging(self):
        """Inicia el registro de datos"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(self.log_dir, f"obd_log_{timestamp}.csv")
            with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'PID', 'Name', 'Value', 'Unit'])
            self.active = True
            return True
        except Exception as e:
            self.logger.error(f"Error iniciando el logging: {e}")
            return False

    def log_data(self, data):
        """Registra datos en el archivo CSV"""
        if not self.active or not self.log_file:
            return False
        try:
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                for pid, info in data.items():
                    writer.writerow([
                        timestamp,
                        pid,
                        info.get('name', ''),
                        info.get('value', ''),
                        info.get('unit', '')
                    ])
            return True
        except Exception as e:
            self.logger.error(f"Error registrando datos: {e}")
            return False

    def enable_sqlite(self, enable=True):
        """Habilita o deshabilita el logging en SQLite"""
        self.sqlite_enabled = enable
        if enable:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.sqlite_file = os.path.join(self.log_dir, f"obd_log_{timestamp}.sqlite")
            self.sqlite_conn = sqlite3.connect(self.sqlite_file)
            self._create_sqlite_table()

    def _create_sqlite_table(self):
        """Crea la tabla en la base de datos SQLite si no existe"""
        if self.sqlite_conn:
            c = self.sqlite_conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS obd_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                pid TEXT,
                value REAL
            )''')
            self.sqlite_conn.commit()

    def log_data_row(self, data_row):
        """Registra una fila de datos (dict {pid: valor}) en el log CSV y/o SQLite."""
        if not self.active or not self.log_file:
            return False
        try:
            # CSV
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                for pid, value in data_row.items():
                    writer.writerow([timestamp, pid, '', value, ''])
            # SQLite
            if self.sqlite_enabled and self.sqlite_conn:
                c = self.sqlite_conn.cursor()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                for pid, value in data_row.items():
                    c.execute("INSERT INTO obd_data (timestamp, pid, value) VALUES (?, ?, ?)", (timestamp, pid, value))
                self.sqlite_conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error registrando fila de datos: {e}")
            return False

    def get_status(self):
        """Obtiene el estado actual del logger"""
        try:
            if not self.active or not self.log_file:
                return {'active': False}
            size_bytes = os.path.getsize(self.log_file)
            size_mb = size_bytes / (1024 * 1024)
            return {
                'active': self.active,
                'file': self.log_file,
                'size': f"{size_mb:.2f}MB"
            }
        except Exception as e:
            self.logger.error(f"Error obteniendo estado del logger: {e}")
            return {'active': False}

    def log_pid_selection(self, selected_fast, selected_slow, selected_extended=None):
        """Registra la selección de PIDs en el log para auditoría"""
        try:
            if not self.active or not self.log_file:
                self.start_logging()
            if not self.log_file:
                return False
            with open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                writer.writerow([timestamp, 'PID_SELECTION', 'FAST', ','.join(selected_fast), ''])
                writer.writerow([timestamp, 'PID_SELECTION', 'SLOW', ','.join(selected_slow), ''])
                if selected_extended is not None:
                    writer.writerow([timestamp, 'PID_SELECTION', 'EXTENDED', ','.join(selected_extended), ''])
            return True
        except Exception as e:
            self.logger.error(f"Error registrando selección de PIDs: {e}")
            return False

    def close(self):
        """Cierra las conexiones abiertas (CSV y SQLite)"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
            self.sqlite_conn = None
