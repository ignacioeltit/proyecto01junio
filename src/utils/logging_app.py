import datetime
import logging
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = "app_errors.log"
LEVELS = {"ERROR": "ERROR", "ADVERTENCIA": "ADVERTENCIA", "INFO": "INFO"}


def setup_logging():
    """Configura sistema de logging mejorado con rotación de archivos"""
    # Crear directorio de logs si no existe
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Nombre del archivo con timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"dashboard_{timestamp}.log")

    # Configurar handler con rotación
    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
    )

    # Formato detallado
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)

    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    # Logger específico para la aplicación
    app_logger = logging.getLogger("dashboard")
    app_logger.setLevel(logging.DEBUG)

    # Handler para consola con menos detalle
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    app_logger.addHandler(console)

    return app_logger


def log_evento_app(tipo, mensaje, contexto=None):
    """
    Registra un evento de la app en el archivo de log con timestamp, tipo y contexto.
    Args:
        tipo: 'ERROR', 'ADVERTENCIA', 'INFO'
        mensaje: Mensaje a registrar
        contexto: (opcional) string con información de módulo, función, escenario, etc.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{now}] {tipo.upper()}: {mensaje}"
    if contexto:
        linea += f" | Contexto: {contexto}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except Exception as e:
        print(f"ERROR guardando log: {e}")
        print(f"Mensaje original: {linea}")
