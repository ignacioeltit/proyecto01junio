import random
import math
from flask import Flask, render_template_string, request, jsonify

class EmuladorOBD2:
    """
    Emulador avanzado de OBD-II con modos de conducción y fallas.
    """
    MODOS = ['ralenti', 'ciudad', 'carretera', 'falla']

    def __init__(self):
        self.modo = 'ralenti'
        self.rpm = 800
        self.velocidad = 0
        self.t = 0
        self.falla = None  # Puede ser 'sensor_rpm', 'sensor_vel', 'dtc', etc.

    def set_modo(self, modo):
        if modo in self.MODOS:
            self.modo = modo
            self.t = 0
            self.falla = None

    def set_falla(self, falla):
        self.falla = falla

    def update(self):
        self.t += 1
        if self.modo == 'ralenti':
            self.rpm = 800 + random.randint(-20, 20)
            self.velocidad = 0
        elif self.modo == 'ciudad':
            self.rpm = 900 + int(1200 * abs(math.sin(self.t/15))) + random.randint(-50, 50)
            if self.t % 40 < 10:
                self.velocidad = 0
            elif self.t % 40 < 30:
                self.velocidad = min(60, self.velocidad + random.randint(0, 4))
            else:
                self.velocidad = max(0, self.velocidad - random.randint(0, 6))
        elif self.modo == 'carretera':
            self.rpm = 2200 + int(600 * abs(math.sin(self.t/30))) + random.randint(-40, 40)
            self.velocidad = 90 + int(30 * abs(math.sin(self.t/20))) + random.randint(-5, 5)
        elif self.modo == 'falla':
            # Simula fallas: valores erráticos o imposibles
            if self.falla == 'sensor_rpm':
                self.rpm = random.choice([0, 200, 8000, 3000])
            elif self.falla == 'sensor_vel':
                self.velocidad = random.choice([0, 255, 10, 180])
            elif self.falla == 'dtc':
                self.rpm = 1200
                self.velocidad = 30
            else:
                self.rpm = random.randint(0, 8000)
                self.velocidad = random.randint(0, 200)
        else:
            self.rpm = 800
            self.velocidad = 0

    def send_pid(self, pid_cmd):
        self.update()
        if pid_cmd == '010C':  # RPM
            rpm_val = self.rpm * 4
            A = (rpm_val >> 8) & 0xFF
            B = rpm_val & 0xFF
            return f'410C{A:02X}{B:02X}'
        elif pid_cmd == '010D':  # Velocidad
            return f'410D{int(self.velocidad):02X}'
        else:
            return 'NO DATA'

    def get_status(self):
        return {
            'modo': self.modo,
            'rpm': self.rpm,
            'velocidad': self.velocidad,
            'falla': self.falla
        }

# --- Panel de control Flask ---
app = Flask(__name__)
emu = EmuladorOBD2()

PANEL_HTML = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Panel Emulador OBD-II</title>
    <style>
        body { font-family: Arial; margin: 2em; }
        .status { font-size: 1.2em; margin-bottom: 1em; }
        .boton { margin: 0.5em; padding: 0.5em 1em; font-size: 1em; }
    </style>
</head>
<body>
    <h2>Panel de Control Emulador OBD-II</h2>
    <div class="status" id="status"></div>
    <div>
        <b>Modo:</b>
        <button class="boton" onclick="setModo('ralenti')">Ralentí</button>
        <button class="boton" onclick="setModo('ciudad')">Ciudad</button>
        <button class="boton" onclick="setModo('carretera')">Carretera</button>
        <button class="boton" onclick="setModo('falla')">Falla</button>
    </div>
    <div style="margin-top:1em;">
        <b>Falla:</b>
        <button class="boton" onclick="setFalla('sensor_rpm')">Sensor RPM</button>
        <button class="boton" onclick="setFalla('sensor_vel')">Sensor Velocidad</button>
        <button class="boton" onclick="setFalla('dtc')">DTC</button>
        <button class="boton" onclick="setFalla('')">Sin Falla</button>
    </div>
    <script>
        function actualizar() {
            fetch('/status').then(r => r.json()).then(data => {
                document.getElementById('status').innerHTML =
                    `<b>Modo:</b> ${data.modo} | <b>RPM:</b> ${data.rpm} | <b>Velocidad:</b> ${data.velocidad} km/h | <b>Falla:</b> ${data.falla || 'Ninguna'}`;
            });
        }
        function setModo(modo) {
            fetch('/set_modo', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({modo})}).then(actualizar);
        }
        function setFalla(falla) {
            fetch('/set_falla', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({falla})}).then(actualizar);
        }
        setInterval(actualizar, 1000);
        actualizar();
    </script>
</body>
</html>
'''

@app.route('/')
def panel():
    return render_template_string(PANEL_HTML)

@app.route('/status')
def status():
    return jsonify(emu.get_status())

@app.route('/set_modo', methods=['POST'])
def set_modo():
    modo = request.json.get('modo')
    emu.set_modo(modo)
    return jsonify({'ok': True})

@app.route('/set_falla', methods=['POST'])
def set_falla():
    falla = request.json.get('falla')
    emu.set_falla(falla)
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(port=5001, debug=True)
