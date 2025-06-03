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
    '010C': {
        'cmd': '010C',
        'nombre': 'rpm',
        'desc': 'Revoluciones por minuto (RPM)',
        'desc_en': 'Engine RPM',
        'unidades': 'rpm',
        'bytes': 2,
        'parse': '((A*256)+B)/4',
        'min': 0,
        'max': 16383.75,
        'type': 'int',
        'ejemplo': '410C1A0B -> ((0x1A*256)+0x0B)/4 = 1664.75',
    },
    '010D': {
        'cmd': '010D',
        'nombre': 'vel',
        'desc': 'Velocidad del vehículo',
        'desc_en': 'Vehicle speed',
        'unidades': 'km/h',
        'bytes': 1,
        'parse': 'A',
        'min': 0,
        'max': 255,
        'type': 'int',
        'ejemplo': '410D28 -> 0x28 = 40 km/h',
    },
    '0105': {
        'cmd': '0105',
        'nombre': 'temp',
        'desc': 'Temperatura refrigerante',
        'desc_en': 'Engine coolant temperature',
        'unidades': '°C',
        'bytes': 1,
        'parse': 'A-40',
        'min': -40,
        'max': 215,
        'type': 'int',
        'ejemplo': '41057B -> 0x7B-40 = 83°C',
    },
    '0110': {
        'cmd': '0110',
        'nombre': 'maf',
        'desc': 'Flujo de aire masivo (MAF)',
        'desc_en': 'MAF air flow rate',
        'unidades': 'g/s',
        'bytes': 2,
        'parse': '((A*256)+B)/100',
        'min': 0,
        'max': 655.35,
        'type': 'float',
        'ejemplo': '41101010 -> ((0x10*256)+0x10)/100 = 41.12 g/s',
    },
    '0111': {
        'cmd': '0111',
        'nombre': 'throttle',
        'desc': 'Posición del acelerador (TPS)',
        'desc_en': 'Throttle position',
        'unidades': '%',
        'bytes': 1,
        'parse': '(A*100)/255',
        'min': 0,
        'max': 100,
        'type': 'float',
        'ejemplo': '411164 -> (0x64*100)/255 = 25.1%',
    },
    '012F': {
        'cmd': '012F',
        'nombre': 'fuel_level',
        'desc': 'Nivel de combustible',
        'desc_en': 'Fuel level input',
        'unidades': '%',
        'bytes': 1,
        'parse': '(A*100)/255',
        'min': 0,
        'max': 100,
        'type': 'float',
        'ejemplo': '412F80 -> (0x80*100)/255 = 50.2%',
    },
    # Agrega aquí más PIDs según necesidad
}

# --- Mapeo global PID (hex) <-> nombre legible ---
PID_MAP = {
    '010C': 'rpm',
    '010D': 'vel',
    '0105': 'temp',
    '0110': 'maf',
    '0111': 'throttle',
    '012F': 'fuel_level',
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
    for pid, info in PIDS.items():
        if info.get('nombre') == norm:
            return info
    return None


def agregar_pid(codigo, info):
    """
    Agrega o actualiza un PID en el diccionario centralizado.
    """
    PIDS[codigo] = info
    PID_MAP[codigo] = info.get('nombre', codigo)
    PID_MAP_INV[info.get('nombre', codigo)] = codigo

# --- FIN DEL MÓDULO CENTRALIZADO DE PIds ---
