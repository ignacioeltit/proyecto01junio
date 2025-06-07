import os
import csv
import logging
from datetime import datetime

class DataLogger:
    """Clase para el registro de datos OBD"""
    def __init__(self):
        self.log_dir = "logs"
        self.log_file = None
        self.active = False
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
    # ...existing code (todos los métodos de logging)...
