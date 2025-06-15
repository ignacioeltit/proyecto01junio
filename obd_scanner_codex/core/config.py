"""Application configuration handling."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / 'config.json'

DEFAULT_CONFIG = {
    "obd_url": "socket://192.168.0.10:35000",
    "simulator": False,
    "debug": False
}

@dataclass
class Config:
    """Application settings."""

    obd_url: str = DEFAULT_CONFIG["obd_url"]
    simulator: bool = DEFAULT_CONFIG["simulator"]
    debug: bool = DEFAULT_CONFIG["debug"]

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**{**DEFAULT_CONFIG, **data})
        return cls()

    def save(self) -> None:
        CONFIG_FILE.write_text(json.dumps(self.__dict__, indent=2), encoding='utf-8')
