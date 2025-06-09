"""
Pruebas básicas para ELM327Interface
"""
import unittest
from src.core.elm327_interface import ELM327Interface

class TestELM327Interface(unittest.TestCase):
    def test_connect(self):
        elm = ELM327Interface()
        self.assertTrue(elm.connect())
        elm.close()

    def test_send_command(self):
        elm = ELM327Interface()
        elm.connect()
        response = elm.send_command("0100")
        self.assertEqual(response, "OK")
        elm.close()

if __name__ == "__main__":
    unittest.main()
