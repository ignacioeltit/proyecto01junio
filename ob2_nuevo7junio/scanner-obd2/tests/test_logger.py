"""
Pruebas para el logger profesional
"""
import unittest
from src.core.logger import get_logger

class TestLogger(unittest.TestCase):
    def test_logger_creation(self):
        logger = get_logger("test")
        logger.info("Mensaje de prueba INFO")
        logger.error("Mensaje de prueba ERROR")
        self.assertTrue(logger)

if __name__ == "__main__":
    unittest.main()
