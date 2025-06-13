"""
Pruebas unitarias para OBD2Acquisition
"""
import unittest
import asyncio
from obd2_acquisition.core import OBD2Acquisition

class TestOBD2Acquisition(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Usa un puerto simulado o mock para pruebas
        self.acq = OBD2Acquisition(port="/dev/null")

    async def test_connect_disconnect(self):
        try:
            await self.acq.connect()
        except Exception:
            pass  # Esperado en /dev/null
        self.assertFalse(self.acq.connected)  # No debe conectar realmente

    async def test_send_command(self):
        with self.assertRaises(RuntimeError):
            await self.acq.send_command("010C")

if __name__ == "__main__":
    unittest.main()
