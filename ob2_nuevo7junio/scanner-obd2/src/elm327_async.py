import asyncio
from typing import List, Dict, Any, Optional

class ELM327Async:
    def __init__(self, mode="real"):
        self.mode = mode
        self.connected = False

    async def connect(self):
        await asyncio.sleep(0.1)
        self.connected = True
        return True

    async def close(self):
        self.connected = False

    async def send_command(self, cmd: str) -> str:
        await asyncio.sleep(0.05)
        # Simulación básica para pruebas
        if cmd == "0902":
            return "49 02 01 31 48 47 43 4D 38 32 36 33 33 41 31 32 33 34 35 36"
        if cmd.startswith("01"):
            return "41" + cmd[2:] + " 10 20 30 40"
        return "NO DATA"

    async def read_vin_iso_tp(self) -> Optional[str]:
        resp = await self.send_command("0902")
        # Decodifica VIN de respuesta simulada
        try:
            parts = resp.split()
            vin_bytes = [int(x, 16) for x in parts[3:]]
            vin = ''.join(chr(b) for b in vin_bytes)
            return vin if len(vin) == 17 else None
        except Exception:
            return None

    async def read_vin_at(self) -> Optional[str]:
        # Simulación fallback
        return None

    async def get_supported_pids(self) -> List[str]:
        # Simulación: retorna algunos PIDs
        return ["010C", "010D", "0105", "0142"]

    async def read_pids_iso_tp(self, pids: List[str]) -> Dict[str, Any]:
        # Simulación: retorna valores fijos
        await asyncio.sleep(0.05 * len(pids))
        return {pid: 1234 for pid in pids}

    async def ping(self) -> bool:
        await asyncio.sleep(0.01)
        return self.connected

    async def reconnect(self):
        await self.connect()
