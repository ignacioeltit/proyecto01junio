import re
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Configura aquí el nombre del archivo de log a analizar
default_log = 'app_errors.log'

# Expresión regular para extraer datos de log
LOG_RE = re.compile(r"LOG_OBD2 \| PID=(\w+) \| valor=([\d.]+) \| unidad=([\w/]+)")

def parse_log(filename):
    data = []
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Extrae timestamp si existe
            ts = None
            try:
                ts = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            m = LOG_RE.search(line)
            if m:
                pid, valor, unidad = m.groups()
                data.append({
                    'timestamp': ts,
                    'pid': pid,
                    'valor': float(valor),
                    'unidad': unidad
                })
    return pd.DataFrame(data)

def plot_pids(df, pids, title):
    plt.figure(figsize=(12, 6))
    for pid, label in pids.items():
        sub = df[df['pid'] == pid]
        if not sub.empty:
            x = sub['timestamp'] if sub['timestamp'].notnull().all() else sub.index
            plt.plot(x, sub['valor'], label=label)
    plt.xlabel('Tiempo')
    plt.ylabel('Valor')
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():
    log_file = input(f"Archivo de log a analizar [{default_log}]: ") or default_log
    df = parse_log(log_file)
    if df.empty:
        print("No se encontraron datos OBD2 en el log.")
        return
    # Graficar velocidad y RPM
    plot_pids(df, {'010D': 'Velocidad (km/h)', '010C': 'RPM'}, 'Velocidad y RPM OBD2')
    # Puedes agregar más PIDs si lo deseas

if __name__ == "__main__":
    main()
