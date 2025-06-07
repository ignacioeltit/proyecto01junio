"""
Manejo de protocolos y PIDs OBD-II.
"""
import logging
import time

class ProtocolHandler:
    """Gestor de protocolos y PIDs OBD-II."""
    
    def __init__(self, elm327):
        self.elm327 = elm327
        self.logger = logging.getLogger(__name__)
        self.supported_pids = []
        
    def scan_pids(self):
        """Escanea todos los PIDs soportados."""
        try:
            # Grupos de PIDs a escanear
            groups = ["0100", "0120", "0140", "0160", "0180", "01A0", "01C0"]
            supported = []
            
            self.logger.info("Iniciando escaneo de PIDs...")
            for group in groups:
                pids = self._scan_group(group)
                if pids:
                    supported.extend(pids)
                    self.logger.debug(f"PIDs detectados en {group}: {len(pids)}")
                    
            self.supported_pids = sorted(list(set(supported)))
            self.logger.info(f"Total PIDs soportados: {len(self.supported_pids)}")
            return self.supported_pids
            
        except Exception as e:
            self.logger.error(f"Error escaneando PIDs: {e}")
            return []
            
    def _scan_group(self, group):
        """Escanea un grupo específico de PIDs."""
        try:
            resp = self.elm327.send_pid(group)
            if not resp or "NO DATA" in resp.upper():
                return []
                
            hex_mask = resp.replace(" ", "")
            if not (hex_mask.startswith("41" + group[2:]) and len(hex_mask) >= 8):
                return []
                
            mask = int(hex_mask[4:12], 16)
            base_pid = int(group[2:], 16)
            pids = []
            
            for i in range(32):
                if mask & (1 << (31 - i)):
                    pid = f"01{base_pid + i + 1:02X}"
                    pids.append(pid)
                    
            return pids
            
        except Exception as e:
            self.logger.error(f"Error en grupo {group}: {e}")
            return []
