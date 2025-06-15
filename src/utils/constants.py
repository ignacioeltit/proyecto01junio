# Constantes globales

OPERATION_MODES = {
    "01": "Datos en tiempo real",
    "02": "Datos congelados",
    "03": "Diagnóstico de fallas (DTCs)",
    "04": "Borrar DTCs y resetear MIL",
    "09": "Información del vehículo (VIN, etc.)",
    "WIFI": "Modo WiFi",
    "EMULATOR": "Modo Emulador"
}

DEFAULT_CONFIG = {
    "wifi_ip": "192.168.0.10",
    "wifi_port": 35000,
    "timeout": 5,
    "max_retries": 3
}

# Puedes agregar aquí otras constantes necesarias para el proyecto.
