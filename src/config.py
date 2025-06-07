# Configuración centralizada para All Motors OBD-II Dashboard
from pathlib import Path

# Rutas base
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
PROFILES_DIR = BASE_DIR / "profiles"
CACHE_DIR = BASE_DIR / "cache"

# Configuración de monitoreo
PERFORMANCE_THRESHOLDS = {
    'memory_mb_limit': 500,
    'cpu_percent_limit': 70,
    'read_time_warning': 0.5,
    'decode_time_warning': 0.1,
    'error_rate_warning': 0.1
}

# Configuración de caché
CACHE_SETTINGS = {
    'max_size': 1000,
    'cleanup_interval': 60,
    'entry_ttl': 300
}

# Configuración de diagnóstico
DIAGNOSTIC_SETTINGS = {
    'check_interval': 5,
    'history_size': 60,
    'reconnect_attempts': 3
}

# Configuración OBD
OBD_SETTINGS = {
    'usb_port': 'COM3',
    'wifi_ip': '192.168.0.10',
    'wifi_port': 35000,
    'timeout': 5,
    'max_retries': 3
}

# Parámetros de emulación
EMULATOR_SETTINGS = {
    'update_interval': 0.1,
    'noise_factor': 0.05,
    'correlate_values': True
}

# Asegurar que existan los directorios necesarios
for directory in [LOGS_DIR, PROFILES_DIR, CACHE_DIR]:
    directory.mkdir(exist_ok=True)
