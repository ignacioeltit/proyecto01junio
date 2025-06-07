# Lógica principal de detección automática de vehículos OBD-II

import json
import os
import logging
from typing import Dict, Optional, List

class VehicleIdentifier:
    """Sistema de identificación automática de vehículos OBD-II"""
    def __init__(self, obd_connection):
        self.obd_connection = obd_connection
        self.vehicle_info = {}
        self.detected_pids = {}
        self.logger = logging.getLogger(__name__)
    def detect_vehicle(self):
        """Detecta automáticamente el vehículo conectado"""
        # Leer VIN y Calibration ID
        vin = self._read_pid("0902")
        calibration_id = self._read_pid("0904")
        ecu_name = self._read_pid("090A")
        # Verificar VIN específico
        if vin and "MR0FB8CD3H0320802" in vin:
            profile = self.create_vehicle_profile(vin, calibration_id, ecu_name)
            return profile
        return None

    def get_supported_pids(self):
        """Obtiene lista de PIDs soportados por el vehículo"""
        # Probar PIDs uno por uno (solo ejemplo, puede optimizarse)
        from src.obd.pids_ext import PIDS
        supported = []
        for pid in PIDS:
            resp = self._read_pid(PIDS[pid]["cmd"])
            if resp and "NO DATA" not in resp:
                supported.append(pid)
        return supported

    def create_vehicle_profile(self, vin, calibration_id, ecu_name):
        """Crea perfil específico del vehículo detectado"""
        from src.vehicle_detection.vehicle_database import VEHICLE_DATABASE
        profile = VEHICLE_DATABASE.get("toyota_hilux_2018_diesel", {}).copy()
        profile["vin"] = vin
        profile["calibration_id"] = calibration_id
        profile["ecu_name"] = ecu_name
        profile["vehicle_id"] = "toyota_hilux_2018_diesel"
        return profile

    def _read_pid(self, pid):
        """Envía comando OBD-II y retorna respuesta cruda"""
        try:
            if hasattr(self.obd_connection, 'send_command'):
                return self.obd_connection.send_command(pid)
            elif hasattr(self.obd_connection, 'socket') and self.obd_connection.socket:
                # Enviar comando por socket WiFi
                self.obd_connection.socket.sendall(f"{pid}\r".encode())
                import time
                time.sleep(0.3)
                response = self.obd_connection.socket.recv(512).decode('utf-8', errors='ignore')
                return response
        except Exception as e:
            print(f"Error leyendo PID {pid}: {e}")
        return None
