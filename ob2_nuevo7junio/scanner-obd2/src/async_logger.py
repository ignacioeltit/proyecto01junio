"""
async_logger.py
Logger asíncrono para evitar bloqueos en la escritura de logs.
Utiliza asyncio y un hilo dedicado para escritura en disco.
"""
import asyncio
import logging
from threading import Thread

class AsyncLogger:
    def __init__(self, logfile):
        self.logfile = logfile
        self.queue = asyncio.Queue()
        self._stop = False
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def log(self, level, msg):
        asyncio.get_event_loop().call_soon_threadsafe(self.queue.put_nowait, (level, msg))

    def _run(self):
        import time
        while not self._stop:
            try:
                level, msg = asyncio.run(self.queue.get())
                with open(self.logfile, 'a', encoding='utf-8') as f:
                    f.write(f"{level}: {msg}\n")
            except Exception:
                time.sleep(0.1)

    def stop(self):
        self._stop = True
        self.thread.join()
