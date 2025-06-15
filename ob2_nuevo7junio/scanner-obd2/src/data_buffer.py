"""
Módulo: data_buffer.py
Propósito: Buffer asíncrono para desacoplar la adquisición de datos OBD2 y la actualización de la GUI.
Utiliza asyncio.Queue para máxima compatibilidad con flujos asíncronos y PyQt.
"""
import asyncio

class DataBuffer:
    def __init__(self, maxsize=100):
        self.queue = asyncio.Queue(maxsize=maxsize)

    async def put(self, data):
        await self.queue.put(data)

    async def get(self):
        return await self.queue.get()

    def empty(self):
        return self.queue.empty()

    def qsize(self):
        return self.queue.qsize()

    async def get_all(self):
        items = []
        while not self.queue.empty():
            items.append(await self.queue.get())
        return items
