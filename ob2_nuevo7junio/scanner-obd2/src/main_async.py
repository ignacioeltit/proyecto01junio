import asyncio
from datetime import datetime
from src.async_json_logger import AsyncJSONLogger
from src.pid_cache import PIDCache
from src.obd2_async_utils import read_vin, read_pids_batch
from src.heartbeat import heartbeat
from src.elm327_async import ELM327Async

async def main():
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger = AsyncJSONLogger(session_id)
    elm = ELM327Async(mode="real")
    await elm.connect()
    vin = await read_vin(elm, logger)
    await logger.set_vin(vin)
    pid_cache = PIDCache()
    if vin:
        supported_pids = pid_cache.get(vin) or await elm.get_supported_pids()
        pid_cache.set(vin, supported_pids)
    else:
        supported_pids = await elm.get_supported_pids()
    asyncio.create_task(heartbeat(elm, logger))
    while True:
        readings = await read_pids_batch(elm, supported_pids, logger)
        await asyncio.sleep(0.5)  # Ajustar según latencia real

if __name__ == "__main__":
    asyncio.run(main())
