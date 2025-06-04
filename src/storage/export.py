# --- Exportación dinámica de logs OBD-II ---
# Este módulo centraliza la lógica de exportación para garantizar consistencia y robustez.
# Debe ser llamado desde el dashboard, logger u otros módulos para guardar logs.
# Siempre genera logs completos, con columnas dinámicas según los PIDs monitoreados.
# --- Validación automática de logs OBD-II ---
# Se ejecuta tras cada exportación y notifica al usuario si el archivo cumple los estándares.
# Ver src/storage/validador.py para detalles y criterios de validación.

import csv
from datetime import datetime, timedelta
from .validador import validar_log_csv


def export_dynamic_log(filename, log_data, pids):
    """
    Exporta el log OBD-II de forma dinámica y robusta.
    - Siempre incluye la columna 'escenario' (modo/fase actual) en el encabezado y en cada fila,
      aunque no esté en la lista de PIDs seleccionados.
    - Solo columnas con nombres legibles (ej: 'rpm', 'vel', 'temp', ...).
    - Solo incluye PIDs seleccionados y con datos en al menos un registro.
    - Consistencia total: lo que se muestra en la UI es lo que se exporta.
    - Sin columnas vacías ni duplicadas.
    Uso recomendado: import y llamada desde dashboard/logger.
    """
    if not log_data:
        print(
            "[EXPORT] No hay datos en memoria para exportar. Se generarán datos de prueba."
        )
        now = datetime.now()
        log_data = []
        for i in range(5):
            entry = {pid: "" for pid in pids}
            entry["timestamp"] = (now + timedelta(seconds=i)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if "rpm" in pids:
                entry["rpm"] = str(800 + i * 20)
            if "vel" in pids:
                entry["vel"] = str(i)
            if "temp" in pids:
                entry["temp"] = str(65 + i)
            if "maf" in pids:
                entry["maf"] = str(round(2.0 + 0.1 * i, 2)) if i % 2 == 0 else ""
            entry["escenario"] = "prueba"
            log_data.append(entry)
    # Determina PIDs realmente activos y con datos
    active_pids = set(["timestamp", "escenario"])
    for row in log_data:
        for pid in pids:
            if pid != "timestamp" and row.get(pid) not in (None, "", "None"):
                active_pids.add(pid)
        # Forzar 'escenario' como activo si existe en el registro
        if "escenario" in row:
            active_pids.add("escenario")
    # Ordena según pids originales, pero siempre antepone 'escenario' tras timestamp
    export_pids = ["timestamp", "escenario"] + [
        pid
        for pid in pids
        if pid in active_pids and pid not in ["timestamp", "escenario"]
    ]
    # --- DEDUPLICACIÓN DE PIDs EN EXPORTACIÓN ---
    pid_map = {}
    dedup_pids = []
    for pid in export_pids:
        norm = pid.lower()
        if norm not in pid_map:
            pid_map[norm] = pid
            dedup_pids.append(pid)
        else:
            print(
                f"[EXPORT] Duplicado detectado y eliminado: {pid} "
                f"(normalizado como {norm})"
            )
    export_pids = dedup_pids
    # Limpia los registros para solo exportar columnas activas y sin duplicados
    export_log = []
    for row in log_data:
        export_row = {
            pid: str(row.get(pid, "")) if row.get(pid, "") is not None else ""
            for pid in export_pids
        }
        export_log.append(export_row)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=export_pids)
        writer.writeheader()
        writer.writerows(export_log)
    print(
        f"[EXPORT] Log exportado correctamente en '{filename}' "
        f"con {len(export_log)} registros y columnas: {export_pids}"
    )
    # Validación automática tras exportar
    valido, errores = validar_log_csv(
        filename, [pid for pid in pids if pid != "timestamp"]
    )
    return valido, errores


# --- Ejemplo de uso/documentación para desarrolladores ---
# from src.storage.export import export_dynamic_log
# export_dynamic_log('log.csv', log_data, pids)
# log_data: lista de dicts con los datos de cada registro
# pids: lista de nombres de columna (PIDs seleccionados + 'timestamp')
# Si log_data está vacío, se generan datos de prueba automáticamente.
