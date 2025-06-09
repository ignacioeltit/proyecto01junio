import json
import os
import re

# Cargar base de datos WMI y años
DATA_PATH = os.path.join(os.path.dirname(__file__), 'vin_data.json')

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    VIN_DATA = json.load(f)

WMI_TABLE = VIN_DATA['wmi']
YEAR_TABLE = VIN_DATA['year']


def decode_vin(vin_str: str) -> dict:
    """
    Decodifica un VIN de 17 caracteres según ISO 3779.
    Retorna un diccionario con los campos principales.
    """
    vin = vin_str.strip().upper()
    result = {
        'vin': vin,
        'valid': False,
        'error': '',
        'country': '',
        'manufacturer': '',
        'vehicle_type': '',
        'year': '',
        'plant': '',
        'serial': '',
    }
    if len(vin) != 17:
        result['error'] = 'El VIN debe tener 17 caracteres.'
        return result
    # Checksum (posición 9)
    if not _validate_vin_checksum(vin):
        result['error'] = 'Checksum inválido.'
        return result
    # WMI
    wmi = vin[:3]
    result['country'] = WMI_TABLE.get(wmi, {}).get('country', '')
    result['manufacturer'] = WMI_TABLE.get(wmi, {}).get('manufacturer', '')
    result['vehicle_type'] = WMI_TABLE.get(wmi, {}).get('type', '')
    # Año
    year_code = vin[9]
    result['year'] = YEAR_TABLE.get(year_code, '')
    # Planta
    result['plant'] = vin[10]
    # Serie
    result['serial'] = vin[11:]
    result['valid'] = True
    return result

def _validate_vin_checksum(vin: str) -> bool:
    """Valida el checksum del VIN (posición 9)."""
    translit = {
        **{str(i): i for i in range(10)},
        **dict(zip('ABCDEFGHJKLMNPRSTUVWXYZ',
                   [1,2,3,4,5,6,7,8,1,2,3,4,5,7,8,9,2,3,4,5,6,7,8,9]))
    }
    weights = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2]
    total = 0
    for i, c in enumerate(vin):
        v = translit.get(c, 0)
        total += v * weights[i]
    check = total % 11
    check_char = 'X' if check == 10 else str(check)
    return vin[8] == check_char
