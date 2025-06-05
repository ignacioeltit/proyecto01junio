import os
import glob
import shutil

def find_latest_log(pattern="log_*.txt"):
    logs = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return logs[0] if logs else None

def summarize_log(input_path, max_bytes=2_621_440):
    output_path = input_path.replace('.txt', '_resumido.txt')
    file_size = os.path.getsize(input_path)
    if file_size <= max_bytes:
        shutil.copy2(input_path, output_path)
        print(f"[RESUMEN] El log ya es menor a 2.5 MB. Copiado a {output_path}")
        return output_path
    # Si es mayor, recortar desde el final
    with open(input_path, 'rb') as f:
        f.seek(-max_bytes, os.SEEK_END)
        data = f.read()
        # Buscar el primer salto de línea para no cortar una línea
        first_nl = data.find(b'\n')
        if first_nl != -1:
            data = data[first_nl+1:]
    with open(output_path, 'wb') as f:
        f.write(data)
    print(f"[RESUMEN] Log resumido a {output_path} (<=2.5 MB)")
    return output_path

if __name__ == "__main__":
    latest_log = find_latest_log()
    if not latest_log:
        print("[RESUMEN][ERROR] No se encontró log para resumir.")
    else:
        summarize_log(latest_log)
