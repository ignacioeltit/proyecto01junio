"""
Módulo universal de decodificación de PIDs OBD-II (SAE J1979) y soporte para perfiles propietarios.
"""
import json
import os

# Diccionario de PIDs estándar OBD-II (SAE J1979)
STANDARD_PIDS = {
    '010C': {'name': 'RPM', 'bytes': 2, 'formula': lambda A, B: ((A * 256) + B) / 4, 'unit': 'RPM'},
    '010D': {'name': 'Velocidad', 'bytes': 1, 'formula': lambda A: A, 'unit': 'km/h'},
    '0105': {'name': 'Temp Refrigerante', 'bytes': 1, 'formula': lambda A: A - 40, 'unit': '°C'},
    '0110': {'name': 'MAF', 'bytes': 2, 'formula': lambda A, B: ((A * 256) + B) / 100, 'unit': 'g/s'},
    '0111': {'name': 'Throttle', 'bytes': 1, 'formula': lambda A: (A * 100) / 255, 'unit': '%'},
    '0142': {'name': 'Voltaje Batería', 'bytes': 2, 'formula': lambda A, B: ((A * 256) + B) / 1000, 'unit': 'V'},
    # Agrega más PIDs estándar aquí...
}

class PIDDecoder:
    def __init__(self, profile_path=None):
        self.standard_pids = STANDARD_PIDS.copy()
        self.custom_pids = {}
        if profile_path:
            self.load_profile(profile_path)

    def load_profile(self, profile_path):
        """Carga un perfil de decodificación propietario desde un archivo JSON."""
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                self.custom_pids = json.load(f)
        else:
            raise FileNotFoundError(f"Perfil no encontrado: {profile_path}")

    def get_pid_info(self, pid):
        if pid in self.custom_pids:
            return self.custom_pids[pid]
        return self.standard_pids.get(pid)

    def decode(self, pid, data_bytes):
        """Decodifica un PID dado los bytes de datos (como lista de enteros)."""
        info = self.get_pid_info(pid)
        if not info:
            return {'pid': pid, 'value': None, 'name': 'Desconocido', 'unit': ''}
        try:
            if 'formula' in info and callable(info['formula']):
                value = info['formula'](*data_bytes)
            elif 'formula' in info and isinstance(info['formula'], str):
                # Permitir fórmulas en string para perfiles JSON
                value = eval(info['formula'], {}, {'A': data_bytes[0], 'B': data_bytes[1] if len(data_bytes)>1 else 0})
            else:
                value = data_bytes[0] if data_bytes else None
        except Exception as e:
            value = None
        return {'pid': pid, 'value': value, 'name': info.get('name', pid), 'unit': info.get('unit', '')}

    @staticmethod
    def parse_pid_response(pid, hex_response):
        """Convierte una respuesta hexadecimal a lista de enteros para decodificación."""
        # Elimina espacios y cabecera si existe
        hex_data = hex_response.replace(' ', '')
        # Busca el PID en la respuesta y extrae los bytes siguientes
        idx = hex_data.find(pid[2:])
        if idx != -1:
            hex_data = hex_data[idx+len(pid[2:]):]
        # Convierte a bytes
        data_bytes = [int(hex_data[i:i+2], 16) for i in range(0, len(hex_data), 2)]
        return data_bytes

    def decode_from_response(self, pid, hex_response):
        data_bytes = self.parse_pid_response(pid, hex_response)
        return self.decode(pid, data_bytes)

# Utilidad para escanear PIDs soportados
def get_supported_pids(obd_connection):
    """Escanea los PIDs soportados por la ECU usando 01 00, 01 20, ..."""
    supported = set()
    for base in range(0x00, 0xE0, 0x20):
        pid = f"01{base:02X}"
        response = obd_connection.query(pid)
        if not response:
            break
        # Extrae los 4 bytes de soporte
        try:
            hex_data = response.replace(' ', '').replace('>', '')
            idx = hex_data.find(pid[2:])
            if idx != -1:
                hex_data = hex_data[idx+len(pid[2:]):]
            bits = int(hex_data[:8], 16)
            for i in range(32):
                if bits & (1 << (31 - i)):
                    supported.add(f"01{base + i:02X}")
        except:
            continue
    return sorted(supported)
