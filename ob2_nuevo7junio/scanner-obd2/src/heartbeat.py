import asyncio

async def heartbeat(elm, logger, interval=5):
    while True:
        ok = await elm.ping()
        if not ok:
            await logger.log_event("warning", "Heartbeat fallido, reconectando...")
            await elm.reconnect()
        await asyncio.sleep(interval)
