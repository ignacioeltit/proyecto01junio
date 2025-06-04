"""
Módulo centralizado de PIDs OBD-II SAE J1979
-------------------------------------------
Contiene la definición, mapeo y utilidades para todos los PIDs soportados.

- Punto único de verdad: todos los módulos deben importar desde aquí.
- Cada PID tiene: nombre legible, código cmd, descripción, unidades, fórmula de parsing, tipo y ejemplos.
- Incluye funciones utilitarias para búsqueda, normalización y extensión.

Ejemplo de uso:
    from obd.pids_ext import PIDS, normalizar_pid, buscar_pid
    pid = normalizar_pid('010C')  # 'rpm'
    info = buscar_pid('rpm')

Recomendación: agregar o modificar PIDs solo en este archivo.
"""

PIDS = {
    "010C": {
        "cmd": "010C",
        "nombre": "rpm",
        "desc": "Revoluciones por minuto (RPM)",
        "desc_en": "Engine RPM",
        "unidades": "rpm",
        "bytes": 2,
        "parse": "((A*256)+B)/4",
        "min": 0,
        "max": 16383.75,
        "type": "int",
        "ejemplo": "410C1A0B -> ((0x1A*256)+0x0B)/4 = 1664.75",
    },
    "010D": {
        "cmd": "010D",
        "nombre": "vel",
        "desc": "Velocidad del vehículo",
        "desc_en": "Vehicle speed",
        "unidades": "km/h",
        "bytes": 1,
        "parse": "A",
        "min": 0,
        "max": 255,
        "type": "int",
        "ejemplo": "410D28 -> 0x28 = 40 km/h",
    },
    "0105": {
        "cmd": "0105",
        "nombre": "temp",
        "desc": "Temperatura refrigerante",
        "desc_en": "Engine coolant temperature",
        "unidades": "°C",
        "bytes": 1,
        "parse": "A-40",
        "min": -40,
        "max": 215,
        "type": "int",
        "ejemplo": "41057B -> 0x7B-40 = 83°C",
        # El parse_fn se asigna abajo para usar la función robusta
    },
    "010F": {
        "cmd": "010F",
        "nombre": "temp_aire",
        "desc": "Temperatura aire de admisión",
        "desc_en": "Intake air temperature",
        "unidades": "°C",
        "bytes": 1,
        "parse": "A-40",
        "min": -40,
        "max": 215,
        "type": "int",
        "ejemplo": "410F5A -> 0x5A-40 = 50°C",
        # El parse_fn se asigna abajo para usar la función robusta
    },
    # Agrega aquí más PIDs según necesidad
}

# --- Mapeo global PID (hex) <-> nombre legible ---
PID_MAP = {
    "010C": "rpm",
    "010D": "vel",
    "0105": "temp",
    "010F": "temp_aire",
    # Agrega aquí más mapeos si agregas más PIDs
}
PID_MAP_INV = {v: k for k, v in PID_MAP.items()}


def normalizar_pid(pid_code):
    """
    Normaliza cualquier variante de PID (hex o nombre legible) a su nombre
    legible estándar. Si ya es nombre legible, lo retorna igual. Si es hex,
    retorna el nombre legible según el mapeo.
    """
    if pid_code in PID_MAP:
        return PID_MAP[pid_code]
    if pid_code in PID_MAP_INV:
        return pid_code
    return pid_code  # Si no está mapeado, retorna igual


# --- Utilidades de búsqueda y extensión ---


def buscar_pid(query):
    """
    Busca información de un PID por nombre legible, código o alias.
    Retorna el dict de info o None si no existe.
    """
    if query in PIDS:
        return PIDS[query]
    norm = normalizar_pid(query)
    for info in PIDS.values():
        if info.get("nombre") == norm:
            return info
    return None


def agregar_pid(codigo, info):
    """
    Agrega o actualiza un PID en el diccionario centralizado.
    """
    PIDS[codigo] = info
    PID_MAP[codigo] = info.get("nombre", codigo)
    PID_MAP_INV[info.get("nombre", codigo)] = codigo


def parse_temp_refrigerante(resp):
    """
    Extrae la temperatura de refrigerante desde respuestas OBD-II crudas
    Ejemplos de entrada: '41 05 7B', '7E9 03 41 05 74'
    """
    try:
        if not resp or not isinstance(resp, str):
            print("[DEBUG][parse_temp_refrigerante] Entrada vacía o tipo incorrecto:")
            print(str(resp))  # noqa
            return None
        parts = resp.replace('\r', ' ').replace('\n', ' ').split()
        for i in range(len(parts)-2):
            if parts[i] == "41" and parts[i+1] == "05":
                valor_hex = parts[i+2]
                temp_c = int(valor_hex, 16) - 40
                print("[DEBUG][parse_temp_refrigerante] Entrada:")
                print(str(resp))
                print("Hex:", str(valor_hex))
                print("Temp:", str(temp_c))
                return temp_c
        print("[DEBUG][parse_temp_refrigerante] Secuencia no encontrada en:")
        print(str(resp))
        return None  # No se encontró la secuencia
    except (ValueError, TypeError) as e:
        print("Error de parseo en parse_temp_refrigerante:", e, resp)
        return None


def parse_temp_aire_admision(resp):
    """
    Parsea la respuesta cruda del PID 010F (temperatura aire de admisión).
    Acepta formatos: '41 0F 5A', '410F5A', '7E9 03 41 0F 5A', etc.
    Devuelve temperatura en °C o None si no es válida.
    """
    try:
        if not resp or not isinstance(resp, str):
            print("[DEBUG][parse_temp_aire_admision] Entrada vacía o tipo incorrecto:")
            print(str(resp))
            return None
        # Buscar formato separado por espacios (incluye encabezados extendidos)
        parts = resp.replace('\r', ' ').replace('\n', ' ').split()
        for i in range(len(parts)-2):
            if parts[i] == "41" and parts[i+1] == "0F":
                valor_hex = parts[i+2]
                temp_c = int(valor_hex, 16) - 40
                print("[DEBUG][parse_temp_aire_admision] Entrada:")
                print(str(resp))
                print("Hex:", str(valor_hex))
                print("Temp:", str(temp_c))
                return temp_c
        # Buscar formato compacto (sin espacios, puede venir de emulador o ELM)
        raw_sin_espacios = resp.replace(" ", "") \
            .replace("\r", "").replace("\n", "")
        idx = raw_sin_espacios.find("410F")
        if idx != -1 and len(raw_sin_espacios) >= idx+6:
            valor_hex = raw_sin_espacios[idx+4:idx+6]
            temp_c = int(valor_hex, 16) - 40
            print("[DEBUG][parse_temp_aire_admision] Entrada compacta:")
            print(str(resp))
            print("Hex:", str(valor_hex))
            print("Temp:", str(temp_c))
            return temp_c
        print("[DEBUG][parse_temp_aire_admision] Secuencia no encontrada en:")
        print(str(resp))
        return None
    except (ValueError, TypeError) as e:
        print("Error de parseo en parse_temp_aire_admision:", e, resp)
        return None


# Asignar la función de parseo robusta al PID 0105
PIDS["0105"]["parse_fn"] = parse_temp_refrigerante
# Asignar la función de parseo robusta al PID 010F
PIDS["010F"]["parse_fn"] = parse_temp_aire_admision

# --- FIN DEL MÓDULO CENTRALIZADO DE PIds ---
