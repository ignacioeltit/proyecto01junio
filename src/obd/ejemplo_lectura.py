from .connection import OBDConnection
from .elm327 import ELM327
from .pids import PIDS
from src.storage.logger import DataLogger
import time
import sys
import multiprocessing


class EmuladorIPCAdapter:
    """
    Emula la interfaz ELM327 para integración transparente.
    Lee valores de RPM y velocidad desde memoria compartida (IPC).
    """

    def __init__(self, shared_dict):
        self.shared_dict = shared_dict

    def send_pid(self, cmd):
        # Simula respuesta cruda de ELM327 para los PIDs soportados
        if cmd == PIDS['rpm']['cmd']:
            rpm = int(self.shared_dict.get('rpm', 800))
            val = rpm * 4
            A = (val >> 8) & 0xFF
            B = val & 0xFF
            return f'410C{A:02X}{B:02X}'
        elif cmd == PIDS['speed']['cmd']:
            speed = int(self.shared_dict.get('vel', 0))
            return f'410D{speed:02X}'
        return ''


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


def main():
    print('¿Cómo deseas obtener los datos OBD-II?')
    print('  [r] Reales (ELM327)')
    print('  [e] Emulados (Emulador IPC)')
    modo = input('Selecciona una opción [r/e]: ').strip().lower()
    USE_EMULADOR_IPC = (modo == 'e')

    conn = None
    logger = None
    emu_proc = None
    try:
        if USE_EMULADOR_IPC:
            import multiprocessing
            manager = multiprocessing.Manager()
            shared_dict = manager.dict({
                'modo': 'ralenti',
                'falla': None,
                'rpm': 800,
                'vel': 0
            })
            from .emu2_ipc import EmuladorDatos
            emu_proc = EmuladorDatos(shared_dict)
            emu_proc.start()
            elm = EmuladorIPCAdapter(shared_dict)
            logger = DataLogger()
            print('Inicializando Emulador OBD-II (IPC)...')
        else:
            if MODO == 'usb':
                conn = OBDConnection(mode='usb', port=PUERTO_USB)
            else:
                conn = OBDConnection(mode='wifi', ip=IP_WIFI, tcp_port=PUERTO_WIFI)
            conn.connect()
            elm = ELM327(conn)
            logger = DataLogger()
            print('Inicializando ELM327...')
            print(elm.initialize())
        print('Leyendo RPM y velocidad. Presiona Ctrl+C para salir.')
        last_rpm = None
        last_speed = None
        while True:
            # Leer RPM
            error_log = []
            resp_rpm = elm.send_pid(PIDS['rpm']['cmd'])
            print(f'Respuesta cruda RPM: {resp_rpm}')  # Depuración
            rpm = None
            rpm_val = None
            if resp_rpm and '410C' in resp_rpm:
                idx = resp_rpm.find('410C')
                hexdata = resp_rpm[idx+4:idx+8]  # 2 bytes después de 410C
                # Validar longitud y caracteres hexadecimales
                if len(hexdata) == 4 and all(c in '0123456789ABCDEFabcdef' for c in hexdata):
                    try:
                        A = int(hexdata[:2], 16)
                        B = int(hexdata[2:], 16)
                        rpm_val = ((A * 256) + B) // 4
                    except Exception as e:
                        error_log.append(f"Error decodificando RPM: {e} | hexdata={hexdata}")
                        rpm_val = None
                else:
                    error_log.append(f"Trama RPM inválida: {hexdata}")
                    rpm_val = None
            else:
                error_log.append(f"Respuesta RPM incompleta/corrupta: {resp_rpm}")
                rpm_val = None
            # Filtro de rango y salto brusco
            if rpm_val is not None and 400 <= rpm_val <= 7000:
                if last_rpm is not None:
                    if abs(rpm_val - last_rpm) > 2000:
                        error_log.append(f"Salto abrupto de RPM: {last_rpm} -> {rpm_val}")
                        rpm_val = last_rpm
                last_rpm = rpm_val
                rpm = rpm_val
            else:
                error_log.append(f"RPM fuera de rango o nula: {rpm_val}")
                if last_rpm is not None:
                    rpm = last_rpm
                else:
                    rpm = 0
            # Leer velocidad
            resp_speed = elm.send_pid(PIDS['speed']['cmd'])
            print(f'Respuesta cruda Velocidad: {resp_speed}')  # Depuración
            speed = None
            speed_val = None
            if resp_speed and '410D' in resp_speed:
                idx = resp_speed.find('410D')
                hexdata = resp_speed[idx+4:idx+6]  # 1 byte después de 410D
                if len(hexdata) == 2 and all(c in '0123456789ABCDEFabcdef' for c in hexdata):
                    try:
                        speed_val = int(hexdata, 16)
                    except Exception as e:
                        error_log.append(f"Error decodificando velocidad: {e} | hexdata={hexdata}")
                        speed_val = None
                else:
                    error_log.append(f"Trama velocidad inválida: {hexdata}")
                    speed_val = None
            else:
                error_log.append(f"Respuesta velocidad incompleta/corrupta: {resp_speed}")
                speed_val = None
            if speed_val is not None and 0 <= speed_val <= 300:
                speed = speed_val
            else:
                error_log.append(f"Velocidad fuera de rango o nula: {speed_val}")
                if last_speed is not None:
                    speed = last_speed
                else:
                    speed = 0
            last_speed = speed
            print(f'RPM: {rpm} | Velocidad: {speed} km/h')
            if rpm is not None or speed is not None:
                logger.log(rpm, speed)
            if error_log:
                ts = time.strftime('%Y-%m-%d %H:%M:%S')
                with open('obd_rpm_error.log', 'a', encoding='utf-8') as ferr:
                    for err in error_log:
                        ferr.write(f"{ts} | {err}\n")
            time.sleep(1)
    except KeyboardInterrupt:
        print('Finalizando...')
    finally:
        try:
            if logger:
                logger.close()
        except Exception:
            pass
        try:
            if (not USE_EMULADOR_IPC) and (conn is not None):
                conn.close()
        except Exception:
            pass
        if emu_proc:
            emu_proc.terminate()
            emu_proc.join()


# Nota: En toda la app, la variable de log y UI es 'vel'.
# El término 'velocidad' solo aparece en mensajes o UI.
# No se usa en la base de datos ni en los logs.

if __name__ == "__main__":
    main()
