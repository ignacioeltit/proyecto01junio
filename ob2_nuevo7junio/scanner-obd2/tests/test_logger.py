"""
Pruebas para el logger profesional
"""
import unittest
from src.core.logger import get_logger
import pytest
import asyncio
from src.async_json_logger import AsyncJSONLogger
import os
import json

class TestLogger(unittest.TestCase):
    def test_logger_creation(self):
        logger = get_logger("test")
        logger.info("Mensaje de prueba INFO")
        logger.error("Mensaje de prueba ERROR")
        self.assertTrue(logger)

@pytest.mark.asyncio
async def test_logger_event_and_reading():
    logger = AsyncJSONLogger("testsession5")
    await logger.log_event("info", "Test event")
    await logger.log_readings({"010C": 1234})
    await logger.close()
    # Verifica que el archivo existe y contiene los datos
    path = f"./logs/testsession5.json"
    assert os.path.exists(path)
    with open(path) as f:
        data = json.load(f)
        assert data["readings"]["010C"] == 1234
        assert any(e["message"] == "Test event" for e in data["events"])

if __name__ == "__main__":
    unittest.main()
