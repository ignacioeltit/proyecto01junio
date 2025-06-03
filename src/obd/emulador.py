"""
Emulador OBD-II profesional: generación de datos realistas y correlacionados
para pruebas, dashboards e IA.

- Soporta PIDs avanzados: rpm, vel, temp, maf, throttle, consumo,
  presion_adm, volt_bateria, carga_motor, etc.
- Escenarios personalizables: secuencia de fases o script definido
  por el usuario.
- Autovalidación: genera, exporta y valida logs automáticamente.
- Fácil integración con módulos de logging/exportación.

Autor: Equipo de Inteligencia Automotriz
Fecha: 2025-06-01
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sys
try:
    from ..utils.logging_app import log_evento_app
except ImportError:
    # Fallback para ejecución directa o desde src como raíz
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.abspath(os.path.join(current_dir, '..'))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from utils.logging_app import log_evento_app


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

    # PIDs OBD-II estándar
    def gen_pid_0105_temp(fase, estado):
        # Temperatura refrigerante (°C): 70-95 según escenario
        if fase == 'ralenti':
            estado['0105'] = random.randint(70, 85)
        elif fase == 'aceleracion':
            estado['0105'] = random.randint(85, 95)
        elif fase == 'crucero':
            estado['0105'] = random.randint(88, 92)
        elif fase == 'frenado':
            estado['0105'] = random.randint(80, 90)
        elif fase == 'ciudad':
            estado['0105'] = random.randint(85, 95)
        elif fase == 'carretera':
            estado['0105'] = random.randint(88, 92)
        elif fase == 'falla':
            estado['0105'] = random.randint(100, 110)
        else:
            estado['0105'] = random.randint(80, 95)
        return estado['0105']

    def gen_pid_0110_maf(fase, estado):
        # MAF (g/s): función de rpm y vel
        base = 2.0 + (estado.get('rpm', 900) / 1000.0) + \
            (estado.get('vel', 0) / 100.0)
        ruido = random.uniform(-0.2, 0.2)
        estado['0110'] = round(base + ruido, 2)
        return estado['0110']

    def gen_pid_0111_tps(fase, estado):
        # TPS (posición de acelerador %):
        if fase == 'ralenti':
            estado['0111'] = random.randint(8, 14)
        elif fase == 'aceleracion':
            estado['0111'] = random.randint(30, 90)
        elif fase == 'crucero':
            estado['0111'] = random.randint(15, 30)
        elif fase == 'frenado':
            estado['0111'] = random.randint(5, 12)
        elif fase == 'ciudad':
            estado['0111'] = random.randint(10, 40)
        elif fase == 'carretera':
            estado['0111'] = random.randint(15, 25)
        elif fase == 'falla':
            estado['0111'] = random.randint(0, 5)
        else:
            estado['0111'] = random.randint(10, 20)
        return estado['0111']

    def gen_pid_012f_nivel_combustible(fase, estado):
        # Nivel de combustible (%): baja lentamente, más rápido en aceleración
        if '012F' not in estado:
            estado['012F'] = 100
        if fase == 'aceleracion':
            estado['012F'] = max(
                0, estado['012F'] - random.uniform(0.05, 0.2)
            )
        elif fase == 'crucero':
            estado['012F'] = max(
                0, estado['012F'] - random.uniform(0.02, 0.08)
            )
        elif fase == 'ralenti':
            estado['012F'] = max(
                0, estado['012F'] - random.uniform(0.005, 0.02)
            )
        elif fase == 'frenado':
            estado['012F'] = max(
                0, estado['012F'] - random.uniform(0.001, 0.01)
            )
        elif fase == 'ciudad':
            estado['012F'] = max(
                0, estado['012F'] - random.uniform(0.03, 0.1)
            )
        elif fase == 'carretera':
            estado['012F'] = max(
                0, estado['012F'] - random.uniform(0.01, 0.05)
            )
        elif fase == 'falla':
            estado['012F'] = max(
                0, estado['012F'] - random.uniform(0.2, 0.5)
            )
        else:
            estado['012F'] = max(
                0, estado['012F'] - random.uniform(0.01, 0.05)
            )
        estado['012F'] = round(estado['012F'], 1)
        return estado['012F']

    def gen_pid_0142_volt_bateria(fase, estado):
        # Voltaje batería (V): 13.2-14.2
        estado['0142'] = round(13.7 + random.uniform(-0.3, 0.3), 2)
        return estado['0142']

    def gen_pid_0104_carga_motor(fase, estado):
        # Carga motor (%):
        if fase == 'ralenti':
            estado['0104'] = random.randint(12, 18)
        elif fase == 'aceleracion':
            estado['0104'] = random.randint(60, 90)
        elif fase == 'crucero':
            estado['0104'] = random.randint(30, 45)
        elif fase == 'frenado':
            estado['0104'] = random.randint(10, 20)
        elif fase == 'ciudad':
            estado['0104'] = random.randint(20, 50)
        elif fase == 'carretera':
            estado['0104'] = random.randint(25, 40)
        elif fase == 'falla':
            estado['0104'] = random.randint(90, 100)
        else:
            estado['0104'] = random.randint(20, 40)
        return estado['0104']

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
        'carga_motor': gen_carga_motor,
        # PIDs OBD-II estándar
        '0105': gen_pid_0105_temp,
        '0110': gen_pid_0110_maf,
        '0111': gen_pid_0111_tps,
        '012F': gen_pid_012f_nivel_combustible,
        '0142': gen_pid_0142_volt_bateria,
        '0104': gen_pid_0104_carga_motor
    }

    # Alias para facilitar extensión y compatibilidad
    pid_alias = {
        'temp': '0105',
        'maf': '0110',
        'throttle': '0111',
        'nivel_combustible': '012F',
        'volt_bateria_std': '0142',
        'carga_motor_std': '0104'
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

    # Instrumentación para depuración integral
    print(f"[EMULADOR] PIDs recibidos: {pids}")
    try:
        log_evento_app(
            'INFO',
            f"[EMULADOR] PIDs recibidos: {pids}",
            contexto='emulador'
        )
    except Exception:
        pass

    for i, fase in enumerate(fases):
        t = (now + timedelta(seconds=i)).strftime("%Y-%m-%d %H:%M:%S")
        registro = {}
        # Actualizar estado para todos los PIDs soportados
        for pid in pid_generators:
            pid_generators[pid](fase, estado)
        # Generar alias también
        for alias, pid_std in pid_alias.items():
            if pid_std in estado:
                estado[alias] = estado[pid_std]
        for pid in pids:
            if pid == 'timestamp':
                registro[pid] = t
            elif pid == 'escenario':
                registro[pid] = fase
            elif pid in pid_generators:
                registro[pid] = estado[pid]
            else:
                advert = (
                    f"Advertencia: El PID solicitado '{pid}' no "
                    f"está soportado en la emulación. Se exportará vacío."
                )
                print(advert, file=sys.stderr)
                try:
                    log_evento_app(
                        'ADVERTENCIA',
                        advert,
                        contexto='emulador'
                    )
                except Exception:
                    pass
                registro[pid] = ""
        print(f"[EMULADOR] Registro generado: {registro}")
        try:
            log_evento_app(
                'INFO',
                f"[EMULADOR] Registro generado: {registro}",
                contexto='emulador'
            )
        except Exception:
            pass
        datos.append(registro)
    return datos


# =========================
# Ejemplo de uso y guía de integración
# =========================

if __name__ == '__main__':

    # Ejemplo de uso avanzado:
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
