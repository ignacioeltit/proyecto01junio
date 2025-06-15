"""Manage PID definitions and live reading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Callable

import obd

from .simulator import Simulator


class PIDManager:
    """Load PID definitions and handle live streaming."""

    def __init__(self, connection: obd.OBD | None, simulator: Simulator | None, logger) -> None:
        self.connection = connection
        self.simulator = simulator
        self.logger = logger
        self.definitions = self._load_definitions()

    def _load_definitions(self) -> Dict[str, List[Dict[str, str]]]:
        path = Path(__file__).resolve().parent.parent / 'data' / 'pid_definitions.json'
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def supported_pids(self) -> List[str]:
        pids = []
        for group in self.definitions.values():
            for item in group:
                pids.append(item['pid'])
        return pids

    def read_pid(self, pid: str) -> str:
        if self.simulator and not (self.connection and self.connection.is_connected()):
            return self.simulator.read_pid(pid)
        if not self.connection or not self.connection.is_connected():
            return ""
        cmd = obd.commands.get(pid)
        if not cmd:
            return ""
        resp = self.connection.query(cmd)
        return str(resp.value) if resp and not resp.is_null() else ""

    def start_stream(self, pids: List[str], callback: Callable[[str, str], None]):
        if self.simulator and not (self.connection and self.connection.is_connected()):
            self.logger.info("Starting simulator stream")
            from threading import Event, Thread
            stop_event = Event()

            def run():
                import time
                while not stop_event.is_set():
                    for pid in pids:
                        value = self.simulator.read_pid(pid)
                        callback(pid, value)
                    time.sleep(0.5)

            t = Thread(target=run, daemon=True)
            t.start()
            return stop_event
        if not self.connection or not self.connection.is_connected():
            return None
        async_conn = obd.Async(self.connection.port_name, fast=False, timeout=1)
        for pid in pids:
            cmd = obd.commands.get(pid)
            if cmd:
                async_conn.watch(cmd, lambda r, p=pid: callback(p, str(r.value)))
        async_conn.start()
        return async_conn
