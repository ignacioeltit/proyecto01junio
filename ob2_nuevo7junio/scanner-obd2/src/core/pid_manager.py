"""
pid_manager.py - Gestión de PIDs soportados y selección de usuario
"""
import json
from typing import Dict, List, Optional
import os

class PIDManager:
    """
    Clase para gestionar la biblioteca de PIDs OBD-II.
    Permite cargar definiciones, consultar soportados y obtener descripciones.
    Soporta filtrado por protocolo OBD-II.
    """
    SUPPORTED_PROTOCOLS = [
        "ISO 9141-2", "ISO 14230 (KWP2000)", "SAE J1850 VPW", "SAE J1850 PWM", "ISO 15765 (CAN)"
    ]

    def __init__(self, pid_def_path: str):
        self.pid_def_path = pid_def_path
        self.pids: Dict[str, dict] = {}
        self.load_pids()

    def load_pids(self) -> None:
        """Carga las definiciones de PIDs desde un archivo JSON."""
        if not os.path.exists(self.pid_def_path):
            raise FileNotFoundError(f"No se encontró el archivo de PIDs: {self.pid_def_path}")
        with open(self.pid_def_path, 'r', encoding='utf-8') as f:
            self.pids = json.load(f)

    def get_supported_pids(self, supported_codes: List[str], protocol: Optional[str] = None) -> Dict[str, dict]:
        """
        Filtra y retorna solo los PIDs soportados por la ECU actual y el protocolo especificado.
        Si protocol es None, retorna todos los soportados.
        """
        if protocol and protocol not in self.SUPPORTED_PROTOCOLS:
            raise ValueError(f"Protocolo OBD-II no soportado: {protocol}")
        result = {}
        for pid, info in self.pids.items():
            if pid in supported_codes:
                if protocol is None or info.get("protocol") == protocol:
                    result[pid] = info
        return result

    def get_pid_info(self, pid: str) -> Optional[dict]:
        """Devuelve la definición completa de un PID."""
        return self.pids.get(pid)

    def list_all_pids(self, protocol: Optional[str] = None) -> List[str]:
        """
        Lista todos los códigos PID disponibles, opcionalmente filtrados por protocolo.
        """
        if protocol:
            return [pid for pid, info in self.pids.items() if info.get("protocol") == protocol]
        return list(self.pids.keys())

    def get_all_pid_info(self) -> Dict[str, dict]:
        """
        Devuelve el diccionario completo de PIDs cargados, útil para integración directa con el scanner principal.
        """
        return self.pids
