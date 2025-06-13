"""
simulator.py - Lógica de simulación ELM327 (basado en Ircama)
"""
import random

class ELM327Simulator:
    """
    Simulador de respuestas ELM327 para comandos OBD-II estándar.
    """
    def __init__(self):
        self.connected = False
        self.supported_pids = ["010C", "010D", "0105", "0104"]

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    def get_supported_pids(self):
        return self.supported_pids

    def read_pid(self, pid):
        """Simula la lectura de un PID OBD-II."""
        if pid == "010C":  # RPM
            return random.randint(700, 4000)
        elif pid == "010D":  # Velocidad
            return random.randint(0, 120)
        elif pid == "0105":  # Temperatura
            return random.randint(70, 110)
        elif pid == "0104":  # Carga motor
            return random.randint(10, 90)
        else:
            return None
