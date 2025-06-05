import subprocess
import os
import glob
from datetime import datetime

# Configuración
EXPORT_SCRIPT = 'exportar_log_liviano.py'  # Script de exportación
LOG_PATTERN = 'log_*.txt'  # Patrón de logs generados por la app
MAX_LOGS = 1  # Solo el último log


def find_latest_log():
    logs = sorted(glob.glob(LOG_PATTERN), key=os.path.getmtime, reverse=True)
    return logs[0] if logs else None


def export_log():
    latest_log = find_latest_log()
    if not latest_log:
        print('[EXPORT] No se encontró ningún log para exportar.')
        return
    # Nombre dinámico para el CSV
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_csv = f'log_exportado_{now}.csv'
    print(f'[EXPORT] Exportando {latest_log} a {output_csv}...')
    # Ejecutar el script de exportación
    try:
        subprocess.run(['python', EXPORT_SCRIPT, latest_log, output_csv], check=True)
        print(f'[EXPORT] Exportación completada: {output_csv}')
    except Exception as e:
        print(f'[EXPORT][ERROR] Falló la exportación: {e}')


if __name__ == '__main__':
    export_log()
