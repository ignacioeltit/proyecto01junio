import sqlite3
import os

def diagnostico_vpic():
    db_path = "data/vpic_lite.db"
    if not os.path.exists(db_path):
        print("❌ No se encontró el archivo vpic_lite.db.")
        print("👉 Recomendado: Opción B – Migrar desde SQL Server a SQLite.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Vehicle;")
        count = cursor.fetchone()[0]
        conn.close()

        print(f"✅ Base encontrada. Registros en Vehicle: {count}")
        if count > 10:
            print("👉 Recomendado: Opción A – Integrar en la GUI.")
        else:
            print("⚠️ Muy pocos registros.")
            print("👉 Recomendado: Opción B – Rehacer migración o verificar datos.")
    except Exception as e:
        print(f"❌ Error accediendo a la base: {e}")
        print("👉 Recomendado: Opción B – Validar la estructura o rehacer migración.")

# Ejecutar diagnóstico
if __name__ == "__main__":
    diagnostico_vpic()
