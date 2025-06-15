"""Asynchronous session logger."""

from __future__ import annotations

import logging
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)


def setup_logger(debug: bool = False) -> logging.Logger:
    """Configure and return the application logger."""
    log_file = LOG_DIR / 'session.log'
    queue: Queue = Queue(-1)
    handler = QueueHandler(queue)
    logger = logging.getLogger('scanner')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(handler)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    listener = QueueListener(queue, file_handler, console_handler)
    listener.start()
    return logger
