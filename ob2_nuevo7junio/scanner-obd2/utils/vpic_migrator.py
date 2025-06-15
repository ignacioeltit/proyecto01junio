"""
utils/vpic_migrator.py - Utilidades para migrar la base vPIC de SQL Server (.bak) a SQLite
"""
import os
import subprocess
import sqlite3
from typing import List
import pyodbc

# 1. Restaurar la base de datos .bak en SQL Server

def restore_sql_server_database(bak_path: str, db_name: str, sql_instance: str = 'localhost\\SQLEXPRESS'):
    """
    Restaura un archivo .bak en una instancia de SQL Server Express/Developer.
    Requiere permisos de administrador y SQLCMD instalado.
    """
    bak_path = os.path.abspath(bak_path)
    restore_sql = f"RESTORE DATABASE [{db_name}] FROM DISK = N'{bak_path}' WITH REPLACE, RECOVERY;"
    cmd = [
        'sqlcmd',
        '-S', sql_instance,
        '-Q', restore_sql
    ]
    print(f"Ejecutando restauración: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

# 2. Exportar tablas relevantes a SQLite

def export_tables_to_sqlite(sqlserver_conn_str: str, sqlite_path: str, tablas: List[str]):
    """
    Exporta tablas seleccionadas de SQL Server a un archivo SQLite.
    sqlserver_conn_str: cadena de conexión ODBC, ej: 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=vPIC;Trusted_Connection=yes;'
    sqlite_path: ruta destino del .db
    tablas: lista de nombres de tablas a exportar
    """
    import pandas as pd
    sqlite_path = os.path.abspath(sqlite_path)
    with sqlite3.connect(sqlite_path) as sqlite_conn:
        sql_conn = pyodbc.connect(sqlserver_conn_str)
        for tabla in tablas:
            print(f"Exportando tabla: {tabla}")
            df = pd.read_sql(f"SELECT * FROM {tabla}", sql_conn)
            df.to_sql(tabla, sqlite_conn, if_exists='replace', index=False)
        sql_conn.close()
    print(f"Exportación completa a {sqlite_path}")

# 3. Importar tablas relevantes (wrapper)
def importar_tablas(tablas_relevantes: list):
    """
    Wrapper para exportar tablas clave a SQLite desde SQL Server local.
    """
    sqlserver_conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=vPIC;Trusted_Connection=yes;'
    sqlite_path = os.path.join(os.path.dirname(__file__), '../data/vpic_lite.db')
    export_tables_to_sqlite(sqlserver_conn_str, sqlite_path, tablas_relevantes)

# 📦 CONFIGURACIÓN DE SQL SERVER
SQL_SERVER = "localhost"
SQL_DB_NAME = "vPIC"
SQL_USER = "sa"
SQL_PASSWORD = "TuPasswordAquí"  # ← CAMBIA ESTE VALOR POR TU CONTRASEÑA DE SQL SERVER

# 📦 CONFIGURACIÓN DE SQLITE
SQLITE_DIR = "data"
SQLITE_FILE = "vpic_lite.db"
SQLITE_PATH = os.path.join(SQLITE_DIR, SQLITE_FILE)

# 📦 TABLAS A MIGRAR
TABLAS = [
    "Vehicle",
    "Make",
    "Model",
    "Engine",
    "FuelType",
    "BodyClass"
]

def exportar_sqlserver_a_sqlite():
    print("🔍 Iniciando migración desde SQL Server a SQLite...")

    # Crear carpeta data/ si no existe
    if not os.path.exists(SQLITE_DIR):
        os.makedirs(SQLITE_DIR)
        print(f"📁 Carpeta creada: {SQLITE_DIR}")

    # Conexión SQL Server
    print(f"🖥️ Conectando a SQL Server → Base: {SQL_DB_NAME}...")
    conn_sql = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SQL_SERVER};'
        f'DATABASE={SQL_DB_NAME};'
        f'UID={SQL_USER};PWD={SQL_PASSWORD}'
    )
    cursor_sql = conn_sql.cursor()

    # Conexión SQLite
    print(f"🧱 Creando base SQLite en: {SQLITE_PATH}...")
    conn_sqlite = sqlite3.connect(SQLITE_PATH)
    cursor_sqlite = conn_sqlite.cursor()

    # Exportar cada tabla
    for tabla in TABLAS:
        print(f"🔄 Procesando tabla: {tabla}")
        cursor_sql.execute(f"SELECT * FROM {tabla}")
        columnas = [col[0] for col in cursor_sql.description]
        registros = cursor_sql.fetchall()

        placeholders = ",".join(["?"] * len(columnas))
        columnas_sql = ",".join([f'"{c}"' for c in columnas])
        schema_sql = ",".join([f'"{col}" TEXT' for col in columnas])

        cursor_sqlite.execute(f"DROP TABLE IF EXISTS {tabla}")
        cursor_sqlite.execute(f"CREATE TABLE {tabla} ({schema_sql})")
        cursor_sqlite.executemany(
            f"INSERT INTO {tabla} ({columnas_sql}) VALUES ({placeholders})",
            registros
        )
        conn_sqlite.commit()
        print(f"✅ {tabla} exportada: {len(registros)} registros")

    conn_sql.close()
    conn_sqlite.close()

    print("\n🎉 MIGRACIÓN COMPLETA")
    print(f"📦 Archivo final generado en: {SQLITE_PATH}")

# Ejecutar migración automáticamente al llamar el script
if __name__ == "__main__":
    bak_path = os.path.expanduser('~/Descargas/vPICList_lite_2025_06.bak')
    db_name = 'vPIC'
    restore_sql_server_database(bak_path, db_name)
    tablas = ['Vehicle', 'WMI', 'Make', 'Model', 'Engine', 'FuelType', 'BodyClass']
    importar_tablas(tablas)
    exportar_sqlserver_a_sqlite()
