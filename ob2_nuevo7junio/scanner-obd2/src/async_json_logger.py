import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class AsyncJSONLogger:
    def __init__(self, session_id: str, log_dir: str = "./logs"):
        self.session_id = session_id
        self.log_path = os.path.join(log_dir, f"{session_id}.json")
        self.queue = asyncio.Queue()
        self.log_data = {
            "session": session_id,
            "vin": None,
            "readings": {},
            "events": []
        }
        os.makedirs(log_dir, exist_ok=True)
        self.writer_task = asyncio.create_task(self._writer())

    async def _writer(self):
        while True:
            entry = await self.queue.get()
            if entry == "CLOSE":
                break
            if entry.get("type") == "reading":
                self.log_data["readings"].update(entry["data"])
            else:
                self.log_data["events"].append(entry)
            with open(self.log_path, "w") as f:
                json.dump(self.log_data, f, indent=2)

    async def log_event(self, type_: str, message: str):
        await self.queue.put({
            "time": datetime.now().isoformat(),
            "type": type_,
            "message": message
        })

    async def log_readings(self, readings: Dict[str, Any]):
        await self.queue.put({"type": "reading", "data": readings})

    async def set_vin(self, vin: Optional[str]):
        self.log_data["vin"] = vin
        with open(self.log_path, "w") as f:
            json.dump(self.log_data, f, indent=2)

    async def close(self):
        await self.queue.put("CLOSE")
        await self.writer_task
