"""
acquisition.py - API de adquisición de datos usando el simulador ELM327
"""
from .simulator import ELM327Simulator

class EmulatorAcquisition:
    """
    API de alto nivel para adquisición de datos OBD-II usando el simulador ELM327.
    """
    def __init__(self):
        self.sim = ELM327Simulator()

    def connect(self):
        return self.sim.connect()

    def disconnect(self):
        self.sim.disconnect()

    def is_connected(self):
        return self.sim.is_connected()

    def get_supported_pids(self):
        return self.sim.get_supported_pids()

    def read_pids(self, pid_list):
        """Lee una lista de PIDs y retorna un diccionario con los valores simulados."""
        return {pid: self.sim.read_pid(pid) for pid in pid_list}
