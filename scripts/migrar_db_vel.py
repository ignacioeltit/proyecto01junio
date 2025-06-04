# Script de migración: elimina la columna 'velocidad' y asegura que solo exista 'vel' en la tabla 'lecturas'.
import sqlite3
import os

DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "obd_log.db"))

conn = sqlite3.connect(DB)
c = conn.cursor()

# 1. Verificar si existe la columna 'velocidad'
c.execute("PRAGMA table_info(lecturas)")
cols = [row[1] for row in c.fetchall()]
if "velocidad" in cols:
    print("Migrando datos de velocidad...")
    # 2. Si hay datos en 'velocidad' y 'vel' está vacía, migrar
    c.execute("UPDATE lecturas SET vel = velocidad WHERE vel IS NULL OR vel = 0")
    # 3. Crear tabla temporal sin 'velocidad'
    c.execute(
        """
        CREATE TABLE lecturas_tmp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            rpm INTEGER,
            vel INTEGER
        )
        """
    )
    c.execute(
        "INSERT INTO lecturas_tmp (id, timestamp, rpm, vel) "
        "SELECT id, timestamp, rpm, vel FROM lecturas"
    )
    c.execute("DROP TABLE lecturas")
    c.execute("ALTER TABLE lecturas_tmp RENAME TO lecturas")
    conn.commit()
    print('Columna "velocidad" eliminada y datos migrados a "vel".')
else:
    print('No se requiere migración. Solo existe la columna "vel".')
conn.close()
print("Migración completada.")
