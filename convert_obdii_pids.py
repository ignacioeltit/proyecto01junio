import json
import os

# Ruta de entrada y salida
INPUT_FILE = 'obdii-pids.json'  # Debes colocar este archivo en el mismo directorio que este script
OUTPUT_FILE = 'pid_definitions_convertido.json'

# Protocolo por defecto
DEFAULT_PROTOCOL = "ISO 9141-2"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"No se encontró {INPUT_FILE}. Descárgalo desde el repo digitalbond/canbus-utils.")
        return
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # El archivo es una lista, el segundo elemento es la lista de PIDs modo 1
    if not isinstance(data, list) or len(data) < 2:
        print("Formato inesperado de obdii-pids.json")
        return
    pids = data[1]
    result = {}
    for info in pids:
        if not isinstance(info, dict):
            continue
        pid = info.get('PID')
        if not pid:
            continue
        pid_code = f"01{pid.upper()}"
        desc = info.get('Desc', '')
        name = desc.split('(')[0].strip() if desc else pid_code
        result[pid_code] = {
            "name": name,
            "desc": desc,
            "unit": "",
            "formula": "",
            "protocol": DEFAULT_PROTOCOL,
            "min": None,
            "max": None
        }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Conversión completada. Archivo generado: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
