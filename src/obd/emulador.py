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
    src_dir = os.path.abspath(os.path.join(current_dir, ".."))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from utils.logging_app import log_evento_app


# =========================
# Función principal de emulación
# =========================
def emular_datos_obd2(
    escenarios: Optional[List[Dict[str, Any]]] = None,
    pids: Optional[List[str]] = None,
    registros_por_fase: int = 1,
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
            "timestamp",
            "rpm",
            "vel",
            "temp",
            "maf",
            "throttle",
            "consumo",
            "presion_adm",
            "volt_bateria",
            "carga_motor",
            "escenario",
        ]
    elif "escenario" not in pids:
        pids = list(pids) + ["escenario"]
    datos = []
    now = datetime.now()
    # Estados iniciales
    estado = {
        "rpm": random.randint(800, 950),
        "vel": 0,
        "temp": random.randint(20, 30),
        "maf": 2.0,
        "throttle": 10,
        "consumo": 0.5,
        "presion_adm": 25,
        "volt_bateria": 13.8,
        "carga_motor": 15,
    }

    def gen_rpm(fase, estado):
        """
        RPM: Ralenti 800-950, aceleración sube, crucero 1800-2500,
        frenado baja.
        """
        if fase == "ralenti":
            estado["rpm"] = random.randint(800, 950)
        elif fase == "aceleracion":
            estado["rpm"] = min(estado["rpm"] + random.randint(200, 400), 4500)
        elif fase == "crucero":
            estado["rpm"] = random.randint(1800, 2500)
        elif fase == "frenado":
            estado["rpm"] = max(estado["rpm"] - random.randint(200, 400), 800)
        return estado["rpm"]

    def gen_vel(fase, estado):
        """
        Velocidad: 0 en ralenti, sube en aceleración, estable en crucero,
        baja en frenado.
        """
        if fase == "ralenti":
            estado["vel"] = max(0, estado["vel"] - random.randint(0, 2))
        elif fase == "aceleracion":
            incremento = int((estado["rpm"] - 800) / 30)
            estado["vel"] = min(estado["vel"] + incremento, 140)
        elif fase == "crucero":
            estado["vel"] = random.randint(90, 120)
        elif fase == "frenado":
            estado["vel"] = max(estado["vel"] - random.randint(15, 30), 0)
        return estado["vel"]

    def gen_temp(fase, estado):
        """
        Temperatura motor: sube hasta 85-95°C, baja si se excede.
        """
        if estado["temp"] < 85:
            estado["temp"] += random.randint(0, 2)
        elif estado["temp"] > 95:
            estado["temp"] -= 1
        return estado["temp"]

    def gen_maf(fase, estado):
        """
        MAF: función de rpm, con ruido.
        """
        estado["maf"] = round(
            1.0 + (estado["rpm"] / 1000.0) + random.uniform(-0.2, 0.2), 2
        )
        return estado["maf"]

    def gen_throttle(fase, estado):
        """
        Apertura de mariposa: 10 en ralenti, sube en aceleración,
        baja en frenado.
        """
        if fase == "ralenti":
            estado["throttle"] = 10
        elif fase == "aceleracion":
            estado["throttle"] = min(100, estado["throttle"] + random.randint(10, 20))
        elif fase == "crucero":
            estado["throttle"] = 20
        elif fase == "frenado":
            estado["throttle"] = max(0, estado["throttle"] - random.randint(10, 20))
        return estado["throttle"]

    def gen_consumo(fase, estado):
        """
        Consumo: bajo en ralenti/frenado, alto en aceleración.
        """
        if fase == "ralenti":
            estado["consumo"] = round(0.4 + random.uniform(-0.05, 0.05), 2)
        elif fase == "aceleracion":
            estado["consumo"] = round(
                1.5 + (estado["rpm"] / 4000) + random.uniform(-0.1, 0.1), 2
            )
        elif fase == "crucero":
            estado["consumo"] = round(0.8 + random.uniform(-0.1, 0.1), 2)
        elif fase == "frenado":
            estado["consumo"] = round(0.3 + random.uniform(-0.05, 0.05), 2)
        return estado["consumo"]

    def gen_presion_adm(fase, estado):
        """
        Presión admisión: baja en ralenti/frenado, alta en aceleración.
        """
        if fase == "ralenti":
            estado["presion_adm"] = random.randint(22, 28)
        elif fase == "aceleracion":
            estado["presion_adm"] = random.randint(80, 100)
        elif fase == "crucero":
            estado["presion_adm"] = random.randint(35, 45)
        elif fase == "frenado":
            estado["presion_adm"] = random.randint(20, 30)
        return estado["presion_adm"]

    def gen_volt_bateria(fase, estado):
        """
        Voltaje batería: 13.5-14.0V, leve ruido.
        """
        estado["volt_bateria"] = round(13.5 + random.uniform(-0.2, 0.2), 2)
        return estado["volt_bateria"]

    def gen_carga_motor(fase, estado):
        """
        Carga motor: baja en ralenti/frenado, alta en aceleración.
        """
        if fase == "ralenti":
            estado["carga_motor"] = random.randint(12, 18)
        elif fase == "aceleracion":
            estado["carga_motor"] = random.randint(60, 90)
        elif fase == "crucero":
            estado["carga_motor"] = random.randint(30, 45)
        elif fase == "frenado":
            estado["carga_motor"] = random.randint(10, 20)
        return estado["carga_motor"]

    # PIDs OBD-II estándar
    def gen_pid_0105_temp(fase, estado):
        # Temperatura refrigerante (°C): 70-95 según escenario
        if fase == "ralenti":
            estado["0105"] = random.randint(70, 85)
        elif fase == "aceleracion":
            estado["0105"] = random.randint(85, 95)
        elif fase == "crucero":
            estado["0105"] = random.randint(88, 92)
        elif fase == "frenado":
            estado["0105"] = random.randint(80, 90)
        elif fase == "ciudad":
            estado["0105"] = random.randint(85, 95)
        elif fase == "carretera":
            estado["0105"] = random.randint(88, 92)
        elif fase == "falla":
            estado["0105"] = random.randint(100, 110)
        else:
            estado["0105"] = random.randint(80, 95)
        return estado["0105"]

    def gen_pid_0110_maf(fase, estado):
        # MAF (g/s): función de rpm y vel
        base = 2.0 + (estado.get("rpm", 900) / 1000.0) + (estado.get("vel", 0) / 100.0)
        ruido = random.uniform(-0.2, 0.2)
        estado["0110"] = round(base + ruido, 2)
        return estado["0110"]

    def gen_pid_0111_tps(fase, estado):
        # TPS (posición de acelerador %):
        if fase == "ralenti":
            estado["0111"] = random.randint(8, 14)
        elif fase == "aceleracion":
            estado["0111"] = random.randint(30, 90)
        elif fase == "crucero":
            estado["0111"] = random.randint(15, 30)
        elif fase == "frenado":
            estado["0111"] = random.randint(5, 12)
        elif fase == "ciudad":
            estado["0111"] = random.randint(10, 40)
        elif fase == "carretera":
            estado["0111"] = random.randint(15, 25)
        elif fase == "falla":
            estado["0111"] = random.randint(0, 5)
        else:
            estado["0111"] = random.randint(10, 20)
        return estado["0111"]

    def gen_pid_012f_nivel_combustible(fase, estado):
        # Nivel de combustible (%): baja lentamente, más rápido en aceleración
        if "012F" not in estado:
            estado["012F"] = 100
        if fase == "aceleracion":
            estado["012F"] = max(0, estado["012F"] - random.uniform(0.05, 0.2))
        elif fase == "crucero":
            estado["012F"] = max(0, estado["012F"] - random.uniform(0.02, 0.08))
        elif fase == "ralenti":
            estado["012F"] = max(0, estado["012F"] - random.uniform(0.005, 0.02))
        elif fase == "frenado":
            estado["012F"] = max(0, estado["012F"] - random.uniform(0.001, 0.01))
        elif fase == "ciudad":
            estado["012F"] = max(0, estado["012F"] - random.uniform(0.03, 0.1))
        elif fase == "carretera":
            estado["012F"] = max(0, estado["012F"] - random.uniform(0.01, 0.05))
        elif fase == "falla":
            estado["012F"] = max(0, estado["012F"] - random.uniform(0.2, 0.5))
        else:
            estado["012F"] = max(0, estado["012F"] - random.uniform(0.01, 0.05))
        estado["012F"] = round(estado["012F"], 1)
        return estado["012F"]

    def gen_pid_0142_volt_bateria(fase, estado):
        # Voltaje batería (V): 13.2-14.2
        estado["0142"] = round(13.7 + random.uniform(-0.3, 0.3), 2)
        return estado["0142"]

    def gen_pid_0104_carga_motor(fase, estado):
        # Carga motor (%):
        if fase == "ralenti":
            estado["0104"] = random.randint(12, 18)
        elif fase == "aceleracion":
            estado["0104"] = random.randint(60, 90)
        elif fase == "crucero":
            estado["0104"] = random.randint(30, 45)
        elif fase == "frenado":
            estado["0104"] = random.randint(10, 20)
        elif fase == "ciudad":
            estado["0104"] = random.randint(20, 50)
        elif fase == "carretera":
            estado["0104"] = random.randint(25, 40)
        elif fase == "falla":
            estado["0104"] = random.randint(90, 100)
        else:
            estado["0104"] = random.randint(20, 40)
        return estado["0104"]

    # Diccionario de dispatch para PIDs soportados
    pid_generators = {
        "rpm": gen_rpm,
        "vel": gen_vel,
        "temp": gen_temp,
        "maf": gen_maf,
        "throttle": gen_throttle,
        "consumo": gen_consumo,
        "presion_adm": gen_presion_adm,
        "volt_bateria": gen_volt_bateria,
        "carga_motor": gen_carga_motor,
        # PIDs OBD-II estándar
        "0105": gen_pid_0105_temp,
        "0110": gen_pid_0110_maf,
        "0111": gen_pid_0111_tps,
        "012F": gen_pid_012f_nivel_combustible,
        "0142": gen_pid_0142_volt_bateria,
        "0104": gen_pid_0104_carga_motor,
    }

    # Alias para facilitar extensión y compatibilidad
    pid_alias = {
        "temp": "0105",
        "maf": "0110",
        "throttle": "0111",
        "nivel_combustible": "012F",
        "volt_bateria_std": "0142",
        "carga_motor_std": "0104",
    }

    # Construir lista de fases expandida
    fases = []
    if escenarios:
        for fase in escenarios:
            fases.extend([fase["fase"]] * (fase["duracion"] * registros_por_fase))
    else:
        fases = (
            ["ralenti"] * (10 * registros_por_fase)
            + ["aceleracion"] * (20 * registros_por_fase)
            + ["crucero"] * (30 * registros_por_fase)
            + ["frenado"] * (10 * registros_por_fase)
        )

    # Instrumentación para depuración integral
    print(f"[EMULADOR] PIDs recibidos: {pids}")
    try:
        log_evento_app(
            "INFO", f"[EMULADOR] PIDs recibidos: {pids}", contexto="emulador"
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
            if pid == "timestamp":
                registro[pid] = t
            elif pid == "escenario":
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
                    log_evento_app("ADVERTENCIA", advert, contexto="emulador")
                except Exception:
                    pass
                registro[pid] = ""
        print(f"[EMULADOR] Registro generado: {registro}")
        try:
            log_evento_app(
                "INFO", f"[EMULADOR] Registro generado: {registro}", contexto="emulador"
            )
        except Exception:
            pass
        datos.append(registro)
    return datos


# =========================
# Ejemplo de uso y guía de integración
# =========================

if __name__ == "__main__":

    # Ejemplo de uso avanzado:
    escenarios = [
        {"fase": "ralenti", "duracion": 10},
        {"fase": "aceleracion", "duracion": 20},
        {"fase": "crucero", "duracion": 30},
        {"fase": "frenado", "duracion": 10},
    ]
    pids = [
        "timestamp",
        "rpm",
        "vel",
        "temp",
        "maf",
        "throttle",
        "carga_motor",
        "presion_adm",
        "volt_bateria",
        "consumo",
        "escenario",
    ]
    datos = emular_datos_obd2(escenarios=escenarios, pids=pids, registros_por_fase=1)
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

# =========================
# Funciones de emulación específicas Toyota Hilux 2018 Diesel
# =========================
def gen_boost_pressure(fase, estado):
    """Genera presión de boost turbo realista para 2GD-FTV"""
    base_pressure = {
        'ralenti': random.uniform(0, 5),
        'aceleracion': random.uniform(80, 180),
        'crucero': random.uniform(40, 90),
        'frenado': random.uniform(0, 20)
    }
    pressure = base_pressure.get(fase, 30)
    estado['boost_pressure'] = round(pressure + random.uniform(-5, 5), 1)
    return estado['boost_pressure']

def gen_turbo_rpm(fase, estado):
    """Genera RPM turbocompresor 2GD-FTV"""
    rpm_motor = estado.get('rpm', 800)
    multiplier = {
        'ralenti': random.uniform(8, 10),
        'aceleracion': random.uniform(12, 15),
        'crucero': random.uniform(10, 12),
        'frenado': random.uniform(8, 9)
    }
    turbo_rpm = rpm_motor * multiplier.get(fase, 10)
    estado['turbo_rpm'] = round(turbo_rpm + random.uniform(-500, 500))
    return estado['turbo_rpm']

def gen_turbo_temp(fase, estado):
    """Genera temperatura turbocompresor"""
    base_temp = {
        'ralenti': random.uniform(60, 80),
        'aceleracion': random.uniform(200, 350),
        'crucero': random.uniform(150, 250),
        'frenado': random.uniform(100, 180)
    }
    temp = base_temp.get(fase, 120)
    estado['turbo_temp'] = round(temp + random.uniform(-10, 10), 1)
    return estado['turbo_temp']

def gen_egr_commanded(fase, estado):
    """Genera EGR comandado para diesel"""
    egr_percent = {
        'ralenti': random.uniform(15, 25),
        'aceleracion': random.uniform(0, 5),
        'crucero': random.uniform(10, 20),
        'frenado': random.uniform(5, 15)
    }
    estado['egr_commanded'] = round(egr_percent.get(fase, 10), 1)
    return estado['egr_commanded']

def gen_egr_temp(fase, estado):
    """Genera temperatura EGR"""
    temp_motor = estado.get('temp', 85)
    egr_temp = temp_motor + random.uniform(20, 60)
    estado['egr_temp'] = round(egr_temp, 1)
    return estado['egr_temp']

def gen_dpf_temperature(fase, estado):
    """Genera temperatura DPF (Diesel Particulate Filter)"""
    base_temp = {
        'ralenti': random.uniform(200, 300),
        'aceleracion': random.uniform(400, 600),
        'crucero': random.uniform(350, 450),
        'frenado': random.uniform(250, 350)
    }
    if random.randint(1, 100) <= 5:
        temp = random.uniform(600, 700)
    else:
        temp = base_temp.get(fase, 300)
    estado['dpf_temperature'] = round(temp + random.uniform(-20, 20), 1)
    return estado['dpf_temperature']

def gen_dpf_differential_pressure(fase, estado):
    """Genera presión diferencial DPF"""
    base_pressure = {
        'ralenti': random.uniform(100, 500),
        'aceleracion': random.uniform(800, 1500),
        'crucero': random.uniform(500, 1000),
        'frenado': random.uniform(200, 600)
    }
    pressure = base_pressure.get(fase, 400)
    estado['dpf_differential_pressure'] = round(pressure + random.uniform(-50, 50))
    return estado['dpf_differential_pressure']

def gen_fuel_rate(fase, estado):
    """Genera tasa consumo combustible diesel L/h"""
    rpm = estado.get('rpm', 800)
    carga = estado.get('carga_motor', 20)
    base_consumption = {
        'ralenti': 1.2,
        'aceleracion': 8.5,
        'crucero': 4.2,
        'frenado': 0.8
    }
    base = base_consumption.get(fase, 2.0)
    consumption = base * (rpm / 1000) * (carga / 50)
    consumption = max(0.5, min(15.0, consumption))
    estado['fuel_rate'] = round(consumption + random.uniform(-0.2, 0.2), 2)
    return estado['fuel_rate']

def gen_fuel_rail_pressure_abs(fase, estado):
    """Genera presión absoluta riel combustible diesel"""
    base_pressure = {
        'ralenti': random.uniform(25000, 35000),
        'aceleracion': random.uniform(45000, 65000),
        'crucero': random.uniform(35000, 50000),
        'frenado': random.uniform(20000, 30000)
    }
    pressure = base_pressure.get(fase, 30000)
    estado['fuel_rail_pressure_abs'] = round(pressure + random.uniform(-2000, 2000))
    return estado['fuel_rail_pressure_abs']

def gen_fuel_rail_absolute_pressure(fase, estado):
    """Alias para fuel_rail_pressure_abs"""
    return gen_fuel_rail_pressure_abs(fase, estado)

def gen_control_module_voltage(fase, estado):
    """Genera voltaje ECU"""
    base_voltage = 13.8
    voltage = base_voltage + random.uniform(-0.3, 0.4)
    estado['control_module_voltage'] = round(voltage, 2)
    return estado['control_module_voltage']

def gen_oil_temp(fase, estado):
    """Genera temperatura aceite motor"""
    temp_motor = estado.get('temp', 85)
    oil_temp = temp_motor + random.uniform(10, 25)
    estado['oil_temp'] = round(oil_temp, 1)
    return estado['oil_temp']

def gen_ambient_temp(fase, estado):
    """Genera temperatura ambiente"""
    base_temp = 22
    temp = base_temp + random.uniform(-5, 8)
    estado['ambient_temp'] = round(temp, 1)
    return estado['ambient_temp']

def gen_intake_air_temp(fase, estado):
    """Genera temperatura aire admisión"""
    ambient = estado.get('ambient_temp', 22)
    turbo_heating = estado.get('boost_pressure', 0) * 0.3
    intake_temp = ambient + turbo_heating + random.uniform(5, 15)
    estado['intake_air_temp'] = round(intake_temp, 1)
    return estado['intake_air_temp']

def update_diesel_interdependencies(estado):
    """Actualiza interdependencias específicas motor diesel"""
    boost = estado.get('boost_pressure', 0)
    if boost > 100:
        estado['fuel_rate'] = estado.get('fuel_rate', 2) * 1.2
    dpf_temp = estado.get('dpf_temperature', 300)
    if dpf_temp > 600:
        estado['egr_temp'] = estado.get('egr_temp', 100) + 50
    rpm_motor = estado.get('rpm', 800)
    if 'turbo_rpm' in estado:
        estado['turbo_rpm'] = rpm_motor * random.uniform(8, 15)

# --- Actualización del diccionario de generadores ---
if 'pid_generators' in globals():
    pid_generators.update({
        'boost_pressure': gen_boost_pressure,
        'turbo_rpm': gen_turbo_rpm,
        'turbo_temp': gen_turbo_temp,
        'egr_commanded': gen_egr_commanded,
        'egr_temp': gen_egr_temp,
        'dpf_temperature': gen_dpf_temperature,
        'dpf_differential_pressure': gen_dpf_differential_pressure,
        'fuel_rate': gen_fuel_rate,
        'fuel_rail_pressure_abs': gen_fuel_rail_pressure_abs,
        'fuel_rail_absolute_pressure': gen_fuel_rail_absolute_pressure,
        'control_module_voltage': gen_control_module_voltage,
        'oil_temp': gen_oil_temp,
        'ambient_temp': gen_ambient_temp,
        'intake_air_temp': gen_intake_air_temp,
    })
else:
    pid_generators = {
        'boost_pressure': gen_boost_pressure,
        'turbo_rpm': gen_turbo_rpm,
        'turbo_temp': gen_turbo_temp,
        'egr_commanded': gen_egr_commanded,
        'egr_temp': gen_egr_temp,
        'dpf_temperature': gen_dpf_temperature,
        'dpf_differential_pressure': gen_dpf_differential_pressure,
        'fuel_rate': gen_fuel_rate,
        'fuel_rail_pressure_abs': gen_fuel_rail_pressure_abs,
        'fuel_rail_absolute_pressure': gen_fuel_rail_absolute_pressure,
        'control_module_voltage': gen_control_module_voltage,
        'oil_temp': gen_oil_temp,
        'ambient_temp': gen_ambient_temp,
        'intake_air_temp': gen_intake_air_temp,
    }

# =========================
# Clase EmuladorOBD para curriculum All Motors
# =========================
class EmuladorOBD:
    """Emulador OBD-II profesional con soporte para curriculum All Motors"""
    
    def __init__(self):
        # Importar configuración
        try:
            from src.config import EMULATOR_SETTINGS
            self.settings = EMULATOR_SETTINGS
        except ImportError:
            self.settings = {
                'update_interval': 0.1,
                'noise_factor': 0.05,
                'correlate_values': True
            }
            
        # Estado inicial del emulador
        self.estado = {
            'rpm': 800,
            'vel': 0,
            'temp': 85,
            'maf': 2.5,
            'throttle': 0,
            'consumo': 0,
            'presion_adm': 101,
            'volt_bateria': 14.2,
            'carga_motor': 0
        }
        
        # Configuración de comportamiento
        self._last_update = datetime.now()
        self._escenario = "ralenti"
        self._fase = 0
        self._ruido = self.settings['noise_factor']
        
    def get_simulated_data(self, pids: List[str]) -> Dict[str, Any]:
        """Genera datos simulados según el escenario actual"""
        self._actualizar_estado()
        
        # Convertir PIDs a formato legible
        pids_legibles = [self._convertir_pid(pid) for pid in pids]
        
        # Generar respuesta con ruido aleatorio
        respuesta = {}
        for pid in pids_legibles:
            if pid in self.estado:
                valor_base = self.estado[pid]
                ruido = random.uniform(-self._ruido, self._ruido) * valor_base
                respuesta[pid] = max(0, valor_base + ruido)
                
        return respuesta
        
    def _actualizar_estado(self):
        """Actualiza estado según tiempo transcurrido y escenario"""
        now = datetime.now()
        delta = (now - self._last_update).total_seconds()
        
        if self._escenario == "ralenti":
            self._actualizar_ralenti(delta)
        elif self._escenario == "aceleracion":
            self._actualizar_aceleracion(delta)
        elif self._escenario == "crucero":
            self._actualizar_crucero(delta)
        elif self._escenario == "frenado":
            self._actualizar_frenado(delta)
            
        self._last_update = now
        
    def _actualizar_ralenti(self, delta):
        """Actualiza estado en ralentí"""
        self.estado['rpm'] = self._suavizar(800, self.estado['rpm'], delta)
        self.estado['vel'] = 0
        self.estado['throttle'] = 0
        self.estado['carga_motor'] = 5
        self._actualizar_dependencias()
        
    def _actualizar_aceleracion(self, delta):
        """Actualiza estado en aceleración"""
        self.estado['rpm'] = self._suavizar(3500, self.estado['rpm'], delta)
        self.estado['vel'] = self._suavizar(60, self.estado['vel'], delta)
        self.estado['throttle'] = 70
        self.estado['carga_motor'] = 80
        self._actualizar_dependencias()
        
    def _actualizar_crucero(self, delta):
        """Actualiza estado en velocidad crucero"""
        self.estado['rpm'] = self._suavizar(2200, self.estado['rpm'], delta)
        self.estado['vel'] = self._suavizar(90, self.estado['vel'], delta)
        self.estado['throttle'] = 20
        self.estado['carga_motor'] = 40
        self._actualizar_dependencias()
        
    def _actualizar_frenado(self, delta):
        """Actualiza estado en frenado"""
        self.estado['rpm'] = self._suavizar(1200, self.estado['rpm'], delta)
        self.estado['vel'] = max(0, self.estado['vel'] - 30 * delta)
        self.estado['throttle'] = 0
        self.estado['carga_motor'] = 10
        self._actualizar_dependencias()
        
    def _actualizar_dependencias(self):
        """Actualiza valores interdependientes"""
        rpm = self.estado['rpm']
        vel = self.estado['vel']
        throttle = self.estado['throttle']
        
        # MAF depende de RPM y throttle
        self.estado['maf'] = (rpm * throttle * 0.001) + 1.5
        
        # Consumo depende de RPM, velocidad y throttle
        if vel > 0:
            self.estado['consumo'] = (rpm * throttle * 0.0001) + 0.5
        else:
            self.estado['consumo'] = 0.2  # Consumo en ralentí
            
        # Presión de admisión depende del throttle
        self.estado['presion_adm'] = 101 + (throttle * 0.5)
        
        # Temperatura según carga
        delta_temp = (self.estado['carga_motor'] - 20) * 0.1
        self.estado['temp'] = min(95, max(82, 85 + delta_temp))
        
    def _suavizar(self, objetivo: float, actual: float, delta: float) -> float:
        """Suaviza transición entre valores"""
        factor = min(1, delta * 2)
        return actual + (objetivo - actual) * factor
        
    def _convertir_pid(self, pid: str) -> str:
        """Convierte PID numérico a nombre legible"""
        pid_map = {
            '010C': 'rpm',
            '010D': 'vel',
            '0105': 'temp',
            '0110': 'maf',
            '0111': 'throttle',
            '015E': 'consumo',
            '010B': 'presion_adm',
            '0142': 'volt_bateria',
            '0104': 'carga_motor'
        }
        return pid_map.get(pid, pid)
