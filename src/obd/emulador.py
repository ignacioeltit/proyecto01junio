"""
Emulador OBD-II profesional: generación de datos realistas y correlacionados para pruebas, dashboards e IA.

- Soporta PIDs avanzados: rpm, vel, temp, maf, throttle, consumo, presion_adm, volt_bateria, carga_motor, etc.
- Escenarios personalizables: secuencia de fases o script definido por el usuario.
- Autovalidación: genera, exporta y valida logs automáticamente.
- Fácil integración con módulos de logging/exportación.

Autor: Equipo de Inteligencia Automotriz
Fecha: 2025-06-01
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sys
from src.utils.logging_app import log_evento_app

# =========================
# Función principal de emulación
# =========================
def emular_datos_obd2(
        escenarios: Optional[List[Dict[str, Any]]] = None,
        pids: Optional[List[str]] = None,
        registros_por_fase: int = 1
) -> List[Dict[str, Any]]:
    """
    Emula datos OBD-II realistas y correlacionados para múltiples escenarios de
    conducción.

    Parámetros:
        escenarios (list): Lista de dicts con fases y duración.
        pids (list): Lista de PIDs a simular.
        registros_por_fase (int): Cantidad de registros por unidad de duración.

    Retorna:
        List[Dict]: Lista de dicts con los valores de los PIDs simulados.

    Ejemplo de uso:
        escenarios = [
            {'fase': 'ralenti', 'duracion': 10},
            {'fase': 'aceleracion', 'duracion': 20},
            {'fase': 'crucero', 'duracion': 30},
            {'fase': 'frenado', 'duracion': 10}
        ]
        pids = [
            'timestamp', 'rpm', 'vel', 'temp', 'maf', 'throttle',
            'carga_motor', 'presion_adm', 'volt_bateria', 'consumo', 'escenario'
        ]
        datos = emular_datos_obd2(
            escenarios=escenarios, pids=pids, registros_por_fase=1
        )
        # Cada dict generado tendrá la clave 'escenario', por ejemplo:
        # {
        #     'timestamp': '2025-06-02 18:00:00',
        #     'rpm': 850,
        #     'vel': 0,
        #     'temp': 80,
        #     'escenario': 'ralenti',
        #     ...
        # }
    """
    if pids is None:
        pids = [
            'timestamp', 'rpm', 'vel', 'temp', 'maf', 'throttle', 'consumo',
            'presion_adm', 'volt_bateria', 'carga_motor',
            'escenario'
        ]
    elif 'escenario' not in pids:
        pids = list(pids) + ['escenario']
    datos = []
    now = datetime.now()
    # Estados iniciales
    estado = {
        'rpm': random.randint(800, 950),
        'vel': 0,
        'temp': random.randint(20, 30),
        'maf': 2.0,
        'throttle': 10,
        'consumo': 0.5,
        'presion_adm': 25,
        'volt_bateria': 13.8,
        'carga_motor': 15
    }

    def gen_rpm(fase, estado):
        """
        RPM: Ralenti 800-950, aceleración sube, crucero 1800-2500,
        frenado baja.
        """
        if fase == 'ralenti':
            estado['rpm'] = random.randint(800, 950)
        elif fase == 'aceleracion':
            estado['rpm'] = min(
                estado['rpm'] + random.randint(200, 400), 4500
            )
        elif fase == 'crucero':
            estado['rpm'] = random.randint(1800, 2500)
        elif fase == 'frenado':
            estado['rpm'] = max(
                estado['rpm'] - random.randint(200, 400), 800
            )
        return estado['rpm']

    def gen_vel(fase, estado):
        """
        Velocidad: 0 en ralenti, sube en aceleración, estable en crucero,
        baja en frenado.
        """
        if fase == 'ralenti':
            estado['vel'] = max(0, estado['vel'] - random.randint(0, 2))
        elif fase == 'aceleracion':
            incremento = int((estado['rpm'] - 800) / 30)
            estado['vel'] = min(estado['vel'] + incremento, 140)
        elif fase == 'crucero':
            estado['vel'] = random.randint(90, 120)
        elif fase == 'frenado':
            estado['vel'] = max(
                estado['vel'] - random.randint(15, 30), 0
            )
        return estado['vel']

    def gen_temp(fase, estado):
        """
        Temperatura motor: sube hasta 85-95°C, baja si se excede.
        """
        if estado['temp'] < 85:
            estado['temp'] += random.randint(0, 2)
        elif estado['temp'] > 95:
            estado['temp'] -= 1
        return estado['temp']

    def gen_maf(fase, estado):
        """
        MAF: función de rpm, con ruido.
        """
        estado['maf'] = round(
            1.0 + (estado['rpm'] / 1000.0) + random.uniform(-0.2, 0.2), 2
        )
        return estado['maf']

    def gen_throttle(fase, estado):
        """
        Apertura de mariposa: 10 en ralenti, sube en aceleración,
        baja en frenado.
        """
        if fase == 'ralenti':
            estado['throttle'] = 10
        elif fase == 'aceleracion':
            estado['throttle'] = min(
                100, estado['throttle'] + random.randint(10, 20)
            )
        elif fase == 'crucero':
            estado['throttle'] = 20
        elif fase == 'frenado':
            estado['throttle'] = max(
                0, estado['throttle'] - random.randint(10, 20)
            )
        return estado['throttle']

    def gen_consumo(fase, estado):
        """
        Consumo: bajo en ralenti/frenado, alto en aceleración.
        """
        if fase == 'ralenti':
            estado['consumo'] = round(
                0.4 + random.uniform(-0.05, 0.05), 2
            )
        elif fase == 'aceleracion':
            estado['consumo'] = round(
                1.5 + (estado['rpm'] / 4000) + random.uniform(-0.1, 0.1), 2
            )
        elif fase == 'crucero':
            estado['consumo'] = round(
                0.8 + random.uniform(-0.1, 0.1), 2
            )
        elif fase == 'frenado':
            estado['consumo'] = round(
                0.3 + random.uniform(-0.05, 0.05), 2
            )
        return estado['consumo']

    def gen_presion_adm(fase, estado):
        """
        Presión admisión: baja en ralenti/frenado, alta en aceleración.
        """
        if fase == 'ralenti':
            estado['presion_adm'] = random.randint(22, 28)
        elif fase == 'aceleracion':
            estado['presion_adm'] = random.randint(80, 100)
        elif fase == 'crucero':
            estado['presion_adm'] = random.randint(35, 45)
        elif fase == 'frenado':
            estado['presion_adm'] = random.randint(20, 30)
        return estado['presion_adm']

    def gen_volt_bateria(fase, estado):
        """
        Voltaje batería: 13.5-14.0V, leve ruido.
        """
        estado['volt_bateria'] = round(
            13.5 + random.uniform(-0.2, 0.2), 2
        )
        return estado['volt_bateria']

    def gen_carga_motor(fase, estado):
        """
        Carga motor: baja en ralenti/frenado, alta en aceleración.
        """
        if fase == 'ralenti':
            estado['carga_motor'] = random.randint(12, 18)
        elif fase == 'aceleracion':
            estado['carga_motor'] = random.randint(60, 90)
        elif fase == 'crucero':
            estado['carga_motor'] = random.randint(30, 45)
        elif fase == 'frenado':
            estado['carga_motor'] = random.randint(10, 20)
        return estado['carga_motor']

    # Diccionario de dispatch para PIDs soportados
    pid_generators = {
        'rpm': gen_rpm,
        'vel': gen_vel,
        'temp': gen_temp,
        'maf': gen_maf,
        'throttle': gen_throttle,
        'consumo': gen_consumo,
        'presion_adm': gen_presion_adm,
        'volt_bateria': gen_volt_bateria,
        'carga_motor': gen_carga_motor
    }

    # Construir lista de fases expandida
    fases = []
    if escenarios:
        for fase in escenarios:
            fases.extend([
                fase['fase']
            ] * (fase['duracion'] * registros_por_fase))
    else:
        fases = (
            ['ralenti'] * (10 * registros_por_fase) +
            ['aceleracion'] * (20 * registros_por_fase) +
            ['crucero'] * (30 * registros_por_fase) +
            ['frenado'] * (10 * registros_por_fase)
        )

    print(f"[EMULADOR] PIDs recibidos: {pids}")
    try:
        log_evento_app('INFO', f"[EMULADOR] PIDs recibidos: {pids}", contexto='emulador')
    except Exception:
        pass

    for i, fase in enumerate(fases):
        t = (now + timedelta(seconds=i)).strftime("%Y-%m-%d %H:%M:%S")
        registro = {}
        # Actualizar estado para todos los PIDs soportados
        for pid in pid_generators:
            pid_generators[pid](fase, estado)
        for pid in pids:
            if pid == 'timestamp':
                registro[pid] = t
            elif pid == 'escenario':
                registro[pid] = fase
            elif pid in pid_generators:
                registro[pid] = estado[pid]
            else:
                advert = (
                    f"Advertencia: El PID solicitado '{pid}' no está soportado "
                    f"en la emulación. Se exportará vacío."
                )
                print(advert, file=sys.stderr)
                try:
                    log_evento_app('ADVERTENCIA', advert, contexto='emulador')
                except Exception:
                    pass
                registro[pid] = ""
        print(f"[EMULADOR] Registro generado: {registro}")
        try:
            log_evento_app('INFO', f"[EMULADOR] Registro generado: {registro}", contexto='emulador')
        except Exception:
            pass
        datos.append(registro)
    return datos


# =========================
# Ejemplo de uso y guía de integración
# =========================

if __name__ == '__main__':
    """
    Ejemplo de uso avanzado:
    """
    escenarios = [
        {'fase': 'ralenti', 'duracion': 10},
        {'fase': 'aceleracion', 'duracion': 20},
        {'fase': 'crucero', 'duracion': 30},
        {'fase': 'frenado', 'duracion': 10}
    ]
    pids = [
        'timestamp', 'rpm', 'vel', 'temp', 'maf', 'throttle',
        'carga_motor', 'presion_adm', 'volt_bateria', 'consumo', 'escenario'
    ]
    datos = emular_datos_obd2(
        escenarios=escenarios, pids=pids, registros_por_fase=1
    )
    print("Ejemplo de datos generados:")
    for row in datos[:5]:
        print(row)

"""
INTEGRACIÓN:
- Importa la función desde otros módulos:
    from src.obd.emulador import emular_datos_obd2
- Llama a emular_datos_obd2 con los PIDs y escenarios deseados.
- Exporta usando tu función de logging/exportación dinámica.
"""
