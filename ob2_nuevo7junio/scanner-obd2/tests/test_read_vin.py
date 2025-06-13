import pytest
import asyncio
from src.async_json_logger import AsyncJSONLogger
from src.obd2_async_utils import read_vin
from src.elm327_async import ELM327Async

@pytest.mark.asyncio
async def test_read_vin_success():
    elm = ELM327Async()
    await elm.connect()
    logger = AsyncJSONLogger("testsession")
    vin = await read_vin(elm, logger)
    assert vin == "1HGCM82633A123456"
    await logger.close()

@pytest.mark.asyncio
async def test_read_vin_fail():
    class DummyELM:
        async def read_vin_iso_tp(self): return None
        async def read_vin_at(self): return None
    logger = AsyncJSONLogger("testsession2")
    vin = await read_vin(DummyELM(), logger)
    assert vin is None
    await logger.close()
