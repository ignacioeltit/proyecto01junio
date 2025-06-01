# Logging y almacenamiento en SQLite

import sqlite3
from datetime import datetime


class DataLogger:
    def __init__(self, db_path='obd_log.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lecturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                rpm INTEGER,
                velocidad INTEGER
            )
        ''')
        self.conn.commit()

    def log(self, rpm, velocidad):
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat(sep=' ', timespec='seconds')
        cursor.execute(
            'INSERT INTO lecturas (timestamp, rpm, velocidad) VALUES (?, ?, ?)',
            (timestamp, rpm, velocidad)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
