"""OBD-II connection wrapper."""

from __future__ import annotations

import obd

from .simulator import Simulator
from .logger import setup_logger


class OBDInterface:
    """Handle connection to an ELM327 device or fallback to simulator."""

    def __init__(self, url: str, use_simulator: bool = False, debug: bool = False) -> None:
        self.url = url
        self.use_simulator = use_simulator
        self.logger = setup_logger(debug)
        self.connection: obd.OBD | None = None
        self.simulator = Simulator() if use_simulator else None

    def connect(self) -> None:
        if self.use_simulator:
            self.logger.info("Using simulator mode")
            return
        try:
            self.connection = obd.OBD(self.url, timeout=1)
            self.logger.info("Connected to OBD on %s", self.url)
        except Exception as exc:
            self.logger.error("Failed to connect: %s", exc)
            self.simulator = Simulator()
            self.use_simulator = True

    def is_connected(self) -> bool:
        if self.use_simulator:
            return True
        return self.connection is not None and self.connection.is_connected()

    def close(self) -> None:
        if self.connection and self.connection.is_connected():
            self.connection.close()
