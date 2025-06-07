# --- utils/obd_parsers.py ---

def safe_cast(val, tipo=float, default=None):
    try:
        return tipo(val)
    except (ValueError, TypeError):
        return default

def parse_pid_response(pid, response, pid_context=None, cmd_context=None):
    """
    Decodifica y procesa la respuesta cruda para el PID solicitado.
    Args:
        pid (str): PID hexadecimal (ej. '010C')
        response (str): Respuesta cruda del OBD (ej. '41 0C 1A F8')
        pid_context (dict): Metadata asociada al PID
        cmd_context (dict): Contexto de comando (puede incluir info de la interfaz, etc.)
    Returns:
        dict: Resultado con clave 'valor', 'unidades', 'raw', 'ok'
    """
    result = {
        'valor': None,
        'unidades': '',
        'raw': response,
        'ok': False
    }
    try:
        bytes_ = response.replace(" ", "").upper()
        # Ejemplo: PID 0C (RPM)
        if pid in ['010C', '0C']:
            if len(bytes_) >= 8:
                A = int(bytes_[4:6], 16)
                B = int(bytes_[6:8], 16)
                rpm = ((A * 256) + B) / 4
                result.update({'valor': rpm, 'unidades': 'rpm', 'ok': True})
        # Ejemplo: PID 0D (VELOCIDAD)
        elif pid in ['010D', '0D']:
            if len(bytes_) >= 6:
                speed = int(bytes_[4:6], 16)
                result.update({'valor': speed, 'unidades': 'km/h', 'ok': True})
        # Ejemplo: PID 05 (Temperatura refrigerante)
        elif pid in ['0105', '05']:
            if len(bytes_) >= 6:
                temp = int(bytes_[4:6], 16) - 40
                result.update({'valor': temp, 'unidades': '°C', 'ok': True})
        # PID 04 (Carga del motor)
        elif pid in ['0104', '04']:
            if len(bytes_) >= 6:
                load = int(bytes_[4:6], 16) * 100 / 255
                result.update({'valor': round(load, 1), 'unidades': '%', 'ok': True})
        # PID 11 (Posición del acelerador)
        elif pid in ['0111', '11']:
            if len(bytes_) >= 6:
                throttle = int(bytes_[4:6], 16) * 100 / 255
                result.update({'valor': round(throttle, 1), 'unidades': '%', 'ok': True})
        # PID 0F (Temperatura de admisión)
        elif pid in ['010F', '0F']:
            if len(bytes_) >= 6:
                temp = int(bytes_[4:6], 16) - 40
                result.update({'valor': temp, 'unidades': '°C', 'ok': True})
        # PID 2F (Nivel de combustible)
        elif pid in ['012F', '2F']:
            if len(bytes_) >= 6:
                fuel = int(bytes_[4:6], 16) * 100 / 255
                result.update({'valor': round(fuel, 1), 'unidades': '%', 'ok': True})
        # PID 42 (Voltaje de control)
        elif pid in ['0142', '42']:
            if len(bytes_) >= 8:
                A = int(bytes_[4:6], 16)
                B = int(bytes_[6:8], 16)
                voltage = ((A * 256) + B) / 1000
                result.update({'valor': round(voltage, 2), 'unidades': 'V', 'ok': True})
        # PID 0B (Presión MAP)
        elif pid in ['010B', '0B']:
            if len(bytes_) >= 6:
                pressure = int(bytes_[4:6], 16)
                result.update({'valor': pressure, 'unidades': 'kPa', 'ok': True})
    except Exception as e:
        result['raw'] += f" | error: {str(e)}"
    return result
