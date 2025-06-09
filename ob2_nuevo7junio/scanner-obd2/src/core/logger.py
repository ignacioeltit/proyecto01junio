"""
logger.py - Configuración de logging profesional para el scanner
"""
import logging
from datetime import datetime
import os

def get_logger(name: str = "scanner-obd2") -> logging.Logger:
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_filename = datetime.now().strftime("log_%Y-%m-%d_%H-%M-%S.txt")
    log_path = os.path.join(logs_dir, log_filename)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)
    return logger
