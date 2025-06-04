import datetime

LOG_FILE = "app_errors.log"

LEVELS = {"ERROR": "ERROR", "ADVERTENCIA": "ADVERTENCIA", "INFO": "INFO"}


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
        print(f"[LOGGING ERROR] No se pudo escribir en el log: {e}")
