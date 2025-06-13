import pytest
import asyncio
from src.async_json_logger import AsyncJSONLogger
from src.obd2_async_utils import read_pids_batch
from src.elm327_async import ELM327Async

@pytest.mark.asyncio
async def test_read_pids_batch():
    elm = ELM327Async()
    await elm.connect()
    logger = AsyncJSONLogger("testsession3")
    pids = ["010C", "010D", "0105", "0142"]
    readings = await read_pids_batch(elm, pids, logger)
    assert all(pid in readings for pid in pids)
    await logger.close()
