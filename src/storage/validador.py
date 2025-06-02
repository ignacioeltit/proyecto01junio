import csv
from typing import List, Tuple

def validar_log_csv(ruta_csv: str, pids_seleccionados: List[str]) -> Tuple[bool, List[str]]:
    """
    Valida un archivo CSV de log OBD-II según los estándares definidos.
    Args:
        ruta_csv: Ruta al archivo CSV a validar.
        pids_seleccionados: Lista de PIDs que deben estar presentes como columnas.
    Returns:
        (valido, lista_errores):
            valido: True si el log es válido, False si hay errores.
            lista_errores: Lista de strings describiendo los problemas encontrados.
    """
    errores = []
    columnas_obligatorias = ['timestamp', 'escenario'] + pids_seleccionados
    try:
        with open(ruta_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            encabezado = reader.fieldnames
            if encabezado is None:
                errores.append('El archivo no tiene encabezado.')
                return False, errores
            # 1. Verificar columnas obligatorias
            faltantes = [col for col in columnas_obligatorias if col not in encabezado]
            if faltantes:
                errores.append(f"Faltan columnas obligatorias: {faltantes}")
            # 2. Revisar filas vacías y valores de 'escenario'
            filas = list(reader)
            if not filas:
                errores.append('El archivo no contiene registros.')
            for i, fila in enumerate(filas):
                if all((v is None or str(v).strip() == '') for v in fila.values()):
                    errores.append(f"Fila {i+2} completamente vacía.")
                if 'escenario' in fila and (fila['escenario'] is None or str(fila['escenario']).strip() == ''):
                    errores.append(f"Fila {i+2} sin valor válido en 'escenario'.")
            # 3. Validar que cada PID seleccionado esté presente y tenga al menos un dato
            for pid in pids_seleccionados:
                if pid in encabezado:
                    if not any(str(f[pid]).strip() != '' for f in filas):
                        errores.append(f"El PID '{pid}' está en el encabezado pero no tiene datos en ningún registro.")
                else:
                    errores.append(f"El PID '{pid}' no está en el encabezado.")
            # 4. Validaciones básicas de coherencia (ejemplo: rpm > 0, vel >= 0)
            for i, fila in enumerate(filas):
                if 'rpm' in fila and fila['rpm']:
                    try:
                        rpm = float(fila['rpm'])
                        if rpm < 0 or rpm > 10000:
                            errores.append(f"Fila {i+2}: valor de 'rpm' fuera de rango (0-10000).")
                    except ValueError:
                        errores.append(f"Fila {i+2}: valor no numérico en 'rpm'.")
                if 'vel' in fila and fila['vel']:
                    try:
                        vel = float(fila['vel'])
                        if vel < 0 or vel > 300:
                            errores.append(f"Fila {i+2}: valor de 'vel' fuera de rango (0-300).")
                    except ValueError:
                        errores.append(f"Fila {i+2}: valor no numérico en 'vel'.")
    except Exception as e:
        errores.append(f"Error al leer el archivo: {e}")
        return False, errores
    return (len(errores) == 0), errores
