"""DTC reader and clearer."""

from __future__ import annotations

from typing import List

import obd

from .simulator import Simulator


class DTCManager:
    """Manage diagnostic trouble codes."""

    def __init__(self, connection: obd.OBD | None, simulator: Simulator | None, logger) -> None:
        self.connection = connection
        self.simulator = simulator
        self.logger = logger

    def read(self) -> List[str]:
        if self.simulator and not (self.connection and self.connection.is_connected()):
            self.logger.info("Reading DTCs from simulator")
            return self.simulator.read_dtcs()
        if not self.connection or not self.connection.is_connected():
            return []
        resp = self.connection.query(obd.commands.GET_DTC)
        if resp.is_null():
            return []
        return ["%s %s" % (code, desc) for code, desc in resp.value]

    def clear(self) -> bool:
        if self.simulator and not (self.connection and self.connection.is_connected()):
            self.logger.info("Clearing DTCs in simulator")
            self.simulator.clear_dtcs()
            return True
        if not self.connection or not self.connection.is_connected():
            return False
        resp = self.connection.query(obd.commands.CLEAR_DTC)
        return not resp.is_null()
