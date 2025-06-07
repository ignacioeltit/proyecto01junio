"""
Emulador específico para Toyota Hilux 2018 Diesel
Extiende el emulador base con PIDs específicos del vehículo
"""
import random
import math
from .emu2 import EmuladorOBD2

class HiluxDieselEmulador(EmuladorOBD2):
    """
    Emulador especializado para Toyota Hilux 2018 Diesel
    Agrega soporte para PIDs específicos:
    - 0123: Presión absoluta riel combustible
    - 0170: Presión boost turbo
    - 0174: RPM turbocompresor
    - 017C: Temperatura DPF
    - 015E: Tasa consumo combustible
    """

    def __init__(self):
        super().__init__()
        self.boost_pressure = 100  # kPa
        self.turbo_rpm = 50000  # RPM
        self.dpf_temp = 200  # °C
        self.fuel_pressure = 1800  # kPa
        self.fuel_rate = 12  # L/h

    def update(self):
        super().update()  # Actualizar RPM y velocidad base
        
        # Calcular valores realistas según el modo
        if self.modo == "ralenti":
            self.boost_pressure = 100 + random.randint(-5, 5)
            self.turbo_rpm = 50000 + random.randint(-1000, 1000)
            self.dpf_temp = 200 + random.randint(-10, 10)
            self.fuel_pressure = 1800 + random.randint(-50, 50)
            self.fuel_rate = 3 + random.random()

        elif self.modo == "ciudad":
            boost_base = 120 + 80 * abs(math.sin(self.t / 15))
            self.boost_pressure = boost_base + random.randint(-10, 10)
            self.turbo_rpm = 80000 + 40000 * abs(math.sin(self.t / 10)) + random.randint(-2000, 2000)
            self.dpf_temp = 300 + 50 * abs(math.sin(self.t / 20)) + random.randint(-15, 15)
            self.fuel_pressure = 2000 + random.randint(-100, 100)
            self.fuel_rate = 8 + 4 * abs(math.sin(self.t / 10)) + random.random()

        elif self.modo == "carretera":
            boost_base = 180 + 40 * abs(math.sin(self.t / 30))
            self.boost_pressure = boost_base + random.randint(-15, 15)
            self.turbo_rpm = 140000 + 20000 * abs(math.sin(self.t / 20)) + random.randint(-3000, 3000)
            self.dpf_temp = 400 + 50 * abs(math.sin(self.t / 25)) + random.randint(-20, 20)
            self.fuel_pressure = 2200 + random.randint(-100, 100)
            self.fuel_rate = 15 + 5 * abs(math.sin(self.t / 15)) + random.random()

        elif self.modo == "falla":
            if self.falla == "sensor_boost":
                self.boost_pressure = random.choice([0, 50, 400])
                self.turbo_rpm = random.choice([0, 250000])
            elif self.falla == "sensor_dpf":
                self.dpf_temp = random.choice([0, 800])
            elif self.falla == "sensor_combustible":
                self.fuel_pressure = random.choice([0, 3000])
                self.fuel_rate = random.choice([0, 30])

    def send_pid(self, pid_cmd):
        """Sobreescribe send_pid para agregar PIDs específicos Hilux"""
        if pid_cmd == "0123":  # Presión riel combustible
            pressure = int(self.fuel_pressure)
            A = (pressure >> 8) & 0xFF
            B = pressure & 0xFF
            return f"4123{A:02X}{B:02X}"

        elif pid_cmd == "0170":  # Presión boost
            pressure = int(self.boost_pressure)
            return f"4170{pressure:02X}"

        elif pid_cmd == "0174":  # RPM Turbo
            rpm = int(self.turbo_rpm)
            A = (rpm >> 8) & 0xFF
            B = rpm & 0xFF
            return f"4174{A:02X}{B:02X}"

        elif pid_cmd == "017C":  # Temperatura DPF
            temp = int(self.dpf_temp)
            return f"417C{temp:02X}"

        elif pid_cmd == "015E":  # Tasa consumo combustible
            rate = int(self.fuel_rate * 20)  # Convertir a 0.05L/h por unidad
            A = (rate >> 8) & 0xFF
            B = rate & 0xFF
            return f"415E{A:02X}{B:02X}"

        return super().send_pid(pid_cmd)  # PIDs base (RPM, velocidad, etc)

    def get_status(self):
        """Extiende el status para incluir valores específicos Hilux"""
        status = super().get_status()
        status.update({
            "boost_pressure": f"{self.boost_pressure:.1f} kPa",
            "turbo_rpm": f"{self.turbo_rpm:,} RPM",
            "dpf_temp": f"{self.dpf_temp:.1f} °C", 
            "fuel_pressure": f"{self.fuel_pressure:.1f} kPa",
            "fuel_rate": f"{self.fuel_rate:.1f} L/h"
        })
        return status
