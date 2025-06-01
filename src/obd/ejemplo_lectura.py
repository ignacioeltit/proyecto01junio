from .connection import OBDConnection
from .elm327 import ELM327
from .pids import PIDS
from src.storage.logger import DataLogger
import time
import sys

# Configura aquí según tu adaptador:
MODO = 'wifi'  # Cambiado a WiFi
PUERTO_USB = 'COM3'  # No se usa en modo WiFi
IP_WIFI = '192.168.0.10'  # IP típica de ELM327 WiFi, cámbiala si es diferente
PUERTO_WIFI = 35000  # Puerto TCP típico para ELM327 WiFi

# Preguntar al usuario si desea usar emulador o conexión real
if len(sys.argv) > 1:
    USE_EMULADOR = sys.argv[1].lower() == 'emulador'
else:
    respuesta = input(
        '¿Deseas usar el emulador OBD-II? (s/n): ')
    USE_EMULADOR = respuesta.strip().lower() == 's'

if MODO == 'usb':
    conn = OBDConnection(mode='usb', port=PUERTO_USB)
else:
    conn = OBDConnection(mode='wifi', ip=IP_WIFI, tcp_port=PUERTO_WIFI)

try:
    if USE_EMULADOR:
        from .emulador import EmuladorOBD
        elm = EmuladorOBD()
        logger = DataLogger()
        print('Inicializando Emulador OBD-II...')
    else:
        conn.connect()
        elm = ELM327(conn)
        logger = DataLogger()
        print('Inicializando ELM327...')
        print(elm.initialize())
    print('Leyendo RPM y velocidad. Presiona Ctrl+C para salir.')
    while True:
        # Leer RPM
        resp_rpm = elm.send_pid(PIDS['rpm']['cmd'])
        print(f'Respuesta cruda RPM: {resp_rpm}')  # Depuración
        rpm = None
        if resp_rpm and '410C' in resp_rpm:
            idx = resp_rpm.find('410C')
            hexdata = resp_rpm[idx+4:idx+8]  # 2 bytes después de 410C
            if len(hexdata) == 4:
                A = int(hexdata[:2], 16)
                B = int(hexdata[2:], 16)
                rpm = ((A * 256) + B) // 4
        # Leer velocidad
        resp_speed = elm.send_pid(PIDS['speed']['cmd'])
        print(f'Respuesta cruda Velocidad: {resp_speed}')  # Depuración
        speed = None
        if resp_speed and '410D' in resp_speed:
            idx = resp_speed.find('410D')
            hexdata = resp_speed[idx+4:idx+6]  # 1 byte después de 410D
            if len(hexdata) == 2:
                speed = int(hexdata, 16)
        print(f'RPM: {rpm} | Velocidad: {speed} km/h')
        if rpm is not None or speed is not None:
            logger.log(rpm, speed)
        time.sleep(1)
except KeyboardInterrupt:
    print('Finalizando...')
finally:
    try:
        logger.close()
    except Exception:
        pass
    if not USE_EMULADOR:
        try:
            conn.close()
        except Exception:
            pass
