from flask import Flask, render_template_string, jsonify
import sqlite3
import threading
import time
import subprocess
import sys

app = Flask(__name__)

# Preguntar si usar emulador o conexión real al iniciar el dashboard
USE_EMULADOR = None
while USE_EMULADOR is None:
    respuesta = input("¿Deseas usar el emulador OBD-II? (s/n): ").strip().lower()
    if respuesta == "s":
        USE_EMULADOR = True
    elif respuesta == "n":
        USE_EMULADOR = False

# Lanzar el proceso de adquisición de datos en modo emulador o real
if USE_EMULADOR:
    proceso = subprocess.Popen(
        [sys.executable, "-m", "src.obd.ejemplo_lectura", "emulador"]
    )
else:
    proceso = subprocess.Popen([sys.executable, "-m", "src.obd.ejemplo_lectura"])

HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard OBD-II</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f4; }
        .container { max-width: 500px; margin: 40px auto; background: #fff; padding: 2em; border-radius: 10px; box-shadow: 0 0 10px #ccc; }
        h1 { text-align: center; }
        .gauge { font-size: 2em; text-align: center; margin: 1em 0; }
        .btn { display: inline-block; margin: 1em 0.5em; padding: 0.5em 1.5em; background: #0078d7; color: #fff; border: none; border-radius: 5px; cursor: pointer; }
        .btn:hover { background: #005fa3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Dashboard OBD-II</h1>
        <div class="gauge">
            <div>RPM: <span id="rpm">-</span></div>
            <div>Velocidad: <span id="velocidad">-</span> km/h</div>
        </div>
        <button class="btn" onclick="window.location='/exportar'">Exportar CSV</button>
        <a class="btn" href="/log">Ver log</a>
    </div>
    <script>
        function actualizar() {
            fetch('/api/ultimo')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('rpm').textContent = d.rpm ?? '-';
                    document.getElementById('velocidad').textContent = d.vel ?? '-';
                });
        }
        setInterval(actualizar, 1000);
        actualizar();
    </script>
</body>
</html>
"""


def get_ultimo_registro():
    conn = sqlite3.connect("obd_log.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rpm, vel FROM lecturas ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"rpm": row[0], "vel": row[1]}
    return {"rpm": None, "vel": None}


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/ultimo")
def api_ultimo():
    return jsonify(get_ultimo_registro())


@app.route("/exportar")
def exportar():
    from src.storage.export import exportar_logs_csv

    ruta = exportar_logs_csv()
    return f"<p>Exportación completada: <b>{ruta}</b></p><a href='/'>Volver</a>"


@app.route("/log")
def ver_log():
    # Muestra las últimas 50 líneas del log en pantalla
    conn = sqlite3.connect("obd_log.db")
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, rpm, vel FROM lecturas ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()
    html = (
        "<h2>Últimos registros</h2>"
        "<table border=1>"
        "<tr><th>Timestamp</th><th>RPM</th><th>Velocidad</th></tr>"
    )
    for t, r, v in rows:
        html += f"<tr><td>{t}</td><td>{r}</td><td>{v}</td></tr>"
    html += '</table><a href="/">Volver</a>'
    return html


HTML = HTML.replace(
    "</div>\n    <script>", '<a class="btn" href="/log">Ver log</a></div>\n    <script>'
)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
