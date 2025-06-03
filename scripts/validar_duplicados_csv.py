import csv
import sys

# Script de validación de logs exportados para buscar duplicados de columnas

def validar_duplicados_csv(path_csv):
    with open(path_csv, encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        lower_headers = [h.lower() for h in headers]
        duplicados = set([h for h in lower_headers if lower_headers.count(h) > 1])
        if duplicados:
            print(f"[VALIDADOR] Duplicados detectados en columnas: {duplicados}")
            return False
        print("[VALIDADOR] No hay columnas duplicadas. Exportación OK.")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python validar_duplicados_csv.py <archivo.csv>")
        sys.exit(1)
    validar_duplicados_csv(sys.argv[1])
