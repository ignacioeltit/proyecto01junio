"""
can_logger.py - Registro de tramas CAN simuladas a CSV o JSON
"""
import csv
import json
import os
from datetime import datetime

def log_can_to_csv(log_dir, message_name, data_dict):
    """
    Registra una trama CAN simulada en un archivo CSV.
    Args:
        log_dir (str): Carpeta de logs
        message_name (str): Nombre del mensaje CAN
        data_dict (dict): Señales y valores
    """
    os.makedirs(log_dir, exist_ok=True)
    fname = os.path.join(log_dir, f"can_log_{message_name}.csv")
    file_exists = os.path.isfile(fname)
    with open(fname, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp'] + list(data_dict.keys()))
        if not file_exists:
            writer.writeheader()
        row = {'timestamp': datetime.now().isoformat()}
        row.update({k: v['value'] for k, v in data_dict.items()})
        writer.writerow(row)

def log_can_to_json(log_dir, message_name, data_dict):
    """
    Registra una trama CAN simulada en un archivo JSON (append line).
    Args:
        log_dir (str): Carpeta de logs
        message_name (str): Nombre del mensaje CAN
        data_dict (dict): Señales y valores
    """
    os.makedirs(log_dir, exist_ok=True)
    fname = os.path.join(log_dir, f"can_log_{message_name}.jsonl")
    row = {'timestamp': datetime.now().isoformat()}
    row.update({k: v['value'] for k, v in data_dict.items()})
    with open(fname, 'a') as f:
        f.write(json.dumps(row) + '\n')
