"""VIN reading and validation."""

from __future__ import annotations

from typing import Optional

import obd
from vininfo import Vin

from .simulator import Simulator


class VINReader:
    """Read and validate the vehicle VIN."""

    def __init__(self, connection: obd.OBD | None, simulator: Simulator | None, logger) -> None:
        self.connection = connection
        self.simulator = simulator
        self.logger = logger

    def read(self) -> Optional[str]:
        vin = None
        if self.simulator and not (self.connection and self.connection.is_connected()):
            self.logger.info("Reading VIN from simulator")
            vin = self.simulator.read_vin()
        elif self.connection and self.connection.is_connected():
            resp = self.connection.query(obd.commands.VIN)
            if resp and not resp.is_null():
                vin = str(resp.value)
        if vin and self._is_valid(vin):
            return vin
        return None

    def _is_valid(self, vin: str) -> bool:
        return len(vin) == 17 and vin.isalnum()

    def decode(self, vin: str) -> str:
        try:
            v = Vin(vin)
            return f"{vin} — {v.country} {v.manufacturer}"
        except Exception:
            return vin
