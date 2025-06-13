"""
utils.py - Utilidades para el módulo de adquisición ELM327 emulado
"""
import logging

def setup_logger(name="elm327_emulator_acquisition"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
