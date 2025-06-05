import re
from datetime import datetime

# Archivo de entrada (puedes cambiarlo si lo necesitas)
input_file = "log_ultimos25min.txt"

# Generar nombre dinámico con fecha y hora actual
now = datetime.now()
output_file = f"log_{now.strftime('%Y%m%d_%H%M')}_liviano.csv"

# Expresión regular para parsear el log
pat = re.compile(r"^\[(.*?)\]\s+(\w+):\s+(.*?)(?:\s*\|\s*Contexto:\s*(.*))?$")

with open(input_file, encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
    fout.write("timestamp,nivel,mensaje,contexto\n")
    for line in fin:
        m = pat.match(line)
        if m:
            ts, nivel, msg, ctx = m.groups()
            ctx = ctx or ""
            # Limpiar comas para CSV
            msg = msg.replace(",", ";")
            ctx = ctx.replace(",", ";")
            fout.write(f'"{ts}","{nivel}","{msg}","{ctx}"\n')

print(f"Log exportado a {output_file}")
