"""
Pruebas unitarias para EmulatorAcquisition
"""
import unittest
from elm327_emulator_acquisition.acquisition import EmulatorAcquisition

class TestEmulatorAcquisition(unittest.TestCase):
    def setUp(self):
        self.acq = EmulatorAcquisition()
        self.acq.connect()

    def test_connection(self):
        self.assertTrue(self.acq.is_connected())

    def test_supported_pids(self):
        pids = self.acq.get_supported_pids()
        self.assertIn("010C", pids)
        self.assertIn("010D", pids)

    def test_read_pids(self):
        data = self.acq.read_pids(["010C", "010D"])
        self.assertIn("010C", data)
        self.assertIn("010D", data)
        self.assertIsInstance(data["010C"], int)
        self.assertIsInstance(data["010D"], int)

if __name__ == "__main__":
    unittest.main()
