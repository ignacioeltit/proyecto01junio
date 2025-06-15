"""Simple OBD-II simulator for offline mode."""

from __future__ import annotations

import random
from typing import Dict, List


class Simulator:
    """Return fake responses for PIDs and DTCs."""

    def __init__(self) -> None:
        self.dtcs: List[str] = ["P0300", "P0420"]

    def read_pid(self, pid: str) -> str:
        if pid == "0C":
            return str(random.randint(800, 3000))
        if pid == "0D":
            return str(random.randint(0, 120))
        if pid == "05":
            return str(random.randint(70, 90))
        if pid == "2F":
            return str(random.randint(0, 100))
        return "0"

    def read_dtcs(self) -> List[str]:
        return self.dtcs

    def clear_dtcs(self) -> None:
        self.dtcs.clear()

    def read_vin(self) -> str:
        return "SIMULATEDVIN12345"
