# Gestión de códigos de diagnóstico (DTC)

def parse_dtc_response(response):
    """
    Parsea la respuesta OBD-II para extraer los códigos DTC.
    """
    # El formato típico es: '43 XX XX XX XX XX XX' (cada par XX es un byte)
    if not response or '43' not in response:
        return []
    idx = response.find('43')
    hexdata = response[idx+2:].replace(' ', '').strip()
    dtcs = []
    for i in range(0, len(hexdata), 4):
        if i+4 <= len(hexdata):
            code = hexdata[i:i+4]
            if code == '0000':
                continue
            dtcs.append(decode_dtc(code))
    return dtcs


def decode_dtc(code):
    """
    Decodifica un código DTC de 4 dígitos hex a formato estándar (ej: P0300).
    """
    if len(code) != 4:
        return code
    first = int(code[0], 16)
    dtc_type = ['P', 'C', 'B', 'U'][first >> 2]
    dtc = dtc_type + str(first & 3) + code[1:]
    return dtc


def build_dtc_commands():
    """
    Devuelve los comandos OBD-II para leer y borrar DTC.
    """
    return {
        'read': '03',
        'clear': '04'
    }
