import random
import time
import math


class EmuladorOBD:
    """
    Emulador de respuestas OBD-II para pruebas sin vehículo real.
    """
    def __init__(self):
        self.rpm = 800  # RPM inicial
        self.velocidad = 0  # Velocidad inicial
        self.t = 0

    def update(self):
        # Simula cambios suaves en RPM y velocidad
        self.t += 1
        self.rpm = 800 + int(700 * abs(math.sin(self.t/10))) \
            + random.randint(-30, 30)
        if self.t % 30 < 10:
            self.velocidad = 0
        elif self.t % 30 < 20:
            self.velocidad = min(120, self.velocidad + random.randint(0, 5))
        else:
            self.velocidad = max(0, self.velocidad - random.randint(0, 5))

    def send_pid(self, pid_cmd):
        self.update()
        if pid_cmd == '010C':  # RPM
            rpm_val = self.rpm * 4
            A = (rpm_val >> 8) & 0xFF
            B = rpm_val & 0xFF
            return f'410C{A:02X}{B:02X}'
        elif pid_cmd == '010D':  # Velocidad
            return f'410D{self.velocidad:02X}'
        else:
            return 'NO DATA'
