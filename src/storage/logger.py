# Logging y almacenamiento en SQLite

import sqlite3
from datetime import datetime
import json


class DataLogger:
    def __init__(self, db_path="obd_log.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lecturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                datos TEXT -- JSON con los valores de los PIDs
            )
        """
        )
        self.conn.commit()

    def log(self, datos: dict):
        """
        Registra una lectura. 'datos' debe ser un dict con los PIDs y valores leídos.
        Ejemplo: {'rpm': 1234, 'vel': 45, '0105': 80}
        """
        try:
            cursor = self.conn.cursor()
            timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
            datos_json = json.dumps(datos, ensure_ascii=False)
            cursor.execute(
                "INSERT INTO lecturas (timestamp, datos) VALUES (?, ?)",
                (timestamp, datos_json),
            )
            self.conn.commit()
        except Exception as e:
            print(f"[Logger] Error al guardar datos: {e}")

    def close(self):
        try:
            self.conn.close()
        except Exception as e:
            print(f"[Logger] Error al cerrar conexión: {e}")
