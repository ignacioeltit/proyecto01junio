import pytest
import asyncio
from src.async_json_logger import AsyncJSONLogger
from src.heartbeat import heartbeat
from src.elm327_async import ELM327Async

@pytest.mark.asyncio
async def test_heartbeat_reconnect():
    elm = ELM327Async()
    await elm.connect()
    logger = AsyncJSONLogger("testsession4")
    # Simula desconexión
    elm.connected = False
    # Ejecuta heartbeat una vez
    async def run_once():
        await heartbeat(elm, logger, interval=0)
    task = asyncio.create_task(run_once())
    await asyncio.sleep(0.1)
    assert elm.connected is True
    await logger.close()
    task.cancel()
