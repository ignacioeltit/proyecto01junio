import asyncio
from typing import List, Dict, Any, Optional

class PIDCache:
    def __init__(self):
        self.cache = {}

    def get(self, vin: str) -> Optional[List[str]]:
        return self.cache.get(vin)

    def set(self, vin: str, pids: List[str]):
        self.cache[vin] = pids
