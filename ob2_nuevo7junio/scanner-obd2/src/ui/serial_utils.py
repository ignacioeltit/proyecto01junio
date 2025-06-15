import glob

def listar_puertos_serial():
    """Devuelve una lista de puertos serie disponibles en macOS (tty y cu)."""
    return sorted(glob.glob('/dev/tty.*') + glob.glob('/dev/cu.*'))
