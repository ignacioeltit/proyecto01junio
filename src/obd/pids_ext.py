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
PIDS["010C"]["parse_fn"] = lambda resp: (
    int(resp.replace(' ', '')[4:8], 16) / 4 if resp and len(resp.replace(' ', '')) >= 8 and resp.replace(' ', '').startswith('410C') else None
)
PIDS["010D"]["parse_fn"] = lambda resp: (
    int(resp.replace(' ', '')[4:6], 16) if resp and len(resp.replace(' ', '')) >= 6 and resp.replace(' ', '').startswith('410D') else None
)

# --- FIN DEL MÓDULO CENTRALIZADO DE PIds ---

# --- Alias por nombre legible para compatibilidad modo real ---
for _hex, _nombre in PID_MAP.items():
    if _nombre not in PIDS:
        PIDS[_nombre] = PIDS[_hex]

# --- PIDs Toyota Hilux 2018 Diesel - Agregados 2025-06-05 ---
# PIDs de Identificación
PIDS["vin"] = {
    "cmd": "0902",
    "desc": "Vehicle Identification Number - Hilux 2018",
    "min": 17,
    "max": 17,
    "parse_fn": lambda resp: parse_vin(resp),
}
PIDS["calibration_id"] = {
    "cmd": "0904",
    "desc": "Calibration ID - ECU Toyota 2GD",
    "min": 0,
    "max": 50,
    "parse_fn": lambda resp: parse_calibration_id(resp),
}
PIDS["ecu_name"] = {
    "cmd": "090A",
    "desc": "ECU Name",
    "min": 0,
    "max": 50,
}
PIDS["supported_pids_mode09"] = {
    "cmd": "0900",
    "desc": "PIDs soportados Mode 09",
    "min": 0,
    "max": 255,
}
# PIDs Específicos Diesel/Turbo
PIDS["fuel_rail_pressure_abs"] = {
    "cmd": "0123",
    "desc": "Presión absoluta riel combustible",
    "min": 0,
    "max": 655350,
    "parse_fn": lambda resp: parse_fuel_rail_pressure_abs(resp),
}
PIDS["boost_pressure"] = {
    "cmd": "0170",
    "desc": "Presión boost turbo",
    "min": 0,
    "max": 512,
    "parse_fn": lambda resp: parse_boost_pressure(resp),
}
PIDS["turbo_rpm"] = {
    "cmd": "0174",
    "desc": "RPM turbocompresor",
    "min": 0,
    "max": 65535,
    "parse_fn": lambda resp: parse_turbo_rpm(resp),
}
PIDS["turbo_temp"] = {
    "cmd": "0175",
    "desc": "Temperatura turbo",
    "min": -40,
    "max": 215,
}
PIDS["egr_commanded"] = {
    "cmd": "012C",
    "desc": "EGR comandado",
    "min": 0,
    "max": 100,
}
PIDS["egr_temp"] = {
    "cmd": "016B",
    "desc": "Temperatura EGR",
    "min": -40,
    "max": 215,
}
PIDS["dpf_differential_pressure"] = {
    "cmd": "017A",
    "desc": "Presión diferencial DPF",
    "min": 0,
    "max": 65535,
}
PIDS["dpf_temperature"] = {
    "cmd": "017C",
    "desc": "Temperatura DPF",
    "min": -40,
    "max": 1200,
    "parse_fn": lambda resp: parse_dpf_temperature(resp),
}
# PIDs Adicionales Motor
PIDS["fuel_rate"] = {
    "cmd": "015E",
    "desc": "Tasa consumo combustible",
    "min": 0,
    "max": 6553.5,
    "parse_fn": lambda resp: parse_fuel_rate(resp),
}
PIDS["control_module_voltage"] = {
    "cmd": "0142",
    "desc": "Voltaje ECU",
    "min": 0,
    "max": 65.535,
    "parse_fn": lambda resp: parse_control_module_voltage(resp),
}
PIDS["maf"] = {
    "cmd": "0110",
    "desc": "Mass Air Flow Rate",
    "min": 0,
    "max": 655.35,
}
PIDS["presion_adm"] = {
    "cmd": "010B",
    "desc": "Intake Manifold Pressure",
    "min": 0,
    "max": 255,
}
PIDS["ambient_temp"] = {
    "cmd": "0146",
    "desc": "Temperatura ambiente",
    "min": -40,
    "max": 215,
}
PIDS["oil_temp"] = {
    "cmd": "015C",
    "desc": "Temperatura aceite motor",
    "min": -40,
    "max": 215,
}
PIDS["fuel_rail_absolute_pressure"] = {
    "cmd": "0159",
    "desc": "Presión absoluta riel",
    "min": 0,
    "max": 655350,
}
PIDS["intake_air_temp"] = {
    "cmd": "010F",
    "desc": "Temperatura aire admisión",
    "min": -40,
    "max": 215,
}

# --- Funciones de parsing específicas para los nuevos PIDs ---
def parse_vin(resp):
    """Parsea VIN específicamente para Toyota Hilux 2018"""
    if not resp:
        return None
    try:
        raw = resp.replace(" ", "")
        if raw.startswith("4902"):
            data_bytes = raw[4:]
            vin = ""
            for i in range(0, len(data_bytes), 2):
                byte_val = int(data_bytes[i:i+2], 16)
                if 32 <= byte_val <= 126:
                    vin += chr(byte_val)
            return vin if len(vin) == 17 else None
    except Exception:
        return None

def parse_calibration_id(resp):
    """Parsea Calibration ID para Toyota Hilux 2018"""
    if not resp:
        return None
    try:
        raw = resp.replace(" ", "")
        if raw.startswith("4904"):
            data_bytes = raw[4:]
            cal_id = ""
            for i in range(0, len(data_bytes), 2):
                byte_val = int(data_bytes[i:i+2], 16)
                if 32 <= byte_val <= 126:
                    cal_id += chr(byte_val)
            return cal_id
    except Exception:
        return None

def parse_fuel_rail_pressure_abs(resp):
    """Parsea presión absoluta riel combustible (PID 0123)"""
    if not resp:
        return None
    try:
        raw = resp.replace(" ", "")
        if raw.startswith("4123") and len(raw) >= 8:
            a = int(raw[4:6], 16)
            b = int(raw[6:8], 16)
            pressure = ((a * 256) + b) * 10
            return pressure
    except Exception:
        return None

def parse_boost_pressure(resp):
    """Parsea presión boost turbo (PID 0170)"""
    if not resp:
        return None
    try:
        raw = resp.replace(" ", "")
        if raw.startswith("4170") and len(raw) >= 8:
            a = int(raw[4:6], 16)
            b = int(raw[6:8], 16)
            boost = ((a * 256) + b) / 128
            return boost
    except Exception:
        return None

def parse_turbo_rpm(resp):
    """Parsea RPM turbocompresor (PID 0174)"""
    if not resp:
        return None
    try:
        raw = resp.replace(" ", "")
        if raw.startswith("4174") and len(raw) >= 8:
            a = int(raw[4:6], 16)
            b = int(raw[6:8], 16)
            rpm = (a * 256) + b
            return rpm
    except Exception:
        return None

def parse_dpf_temperature(resp):
    """Parsea temperatura DPF (PID 017C)"""
    if not resp:
        return None
    try:
        raw = resp.replace(" ", "")
        if raw.startswith("417C") and len(raw) >= 8:
            a = int(raw[4:6], 16)
            b = int(raw[6:8], 16)
            temp = ((a * 256) + b) * 0.1 - 40
            return temp
    except Exception:
        return None

def parse_fuel_rate(resp):
    """Parsea tasa de consumo de combustible (PID 015E)"""
    if not resp:
        return None
    try:
        raw = resp.replace(" ", "")
        if raw.startswith("415E") and len(raw) >= 8:
            a = int(raw[4:6], 16)
            b = int(raw[6:8], 16)
            rate = ((a * 256) + b) * 0.05
            return rate
    except Exception:
        return None

def parse_control_module_voltage(resp):
    """Parsea voltaje ECU (PID 0142) de respuestas simples o múltiples (concatenadas)."""
    if not resp:
        return None
    try:
        # Buscar todas las ocurrencias de 41 42 XX YY
        import re
        # Permite respuestas con o sin espacios
        pattern = re.compile(r"41\s*42\s*([0-9A-Fa-f]{2})\s*([0-9A-Fa-f]{2})")
        matches = pattern.findall(resp)
        if not matches:
            # Buscar también en formato compacto (sin espacios)
            pattern2 = re.compile(r"4142([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})")
            matches = pattern2.findall(resp)
        for a_hex, b_hex in matches:
            a = int(a_hex, 16)
            b = int(b_hex, 16)
            voltage = ((a * 256) + b) * 0.001
            # Solo retorna el primer valor válido encontrado
            return voltage
    except Exception:
        return None
    return None
# --- Fin PIDs Toyota Hilux 2018 Diesel ---
