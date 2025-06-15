import obd
import socket
import json
import time
import os
from typing import List, Tuple, Dict, Any, Optional

# Ruta relativa a la base de datos local de DTCs
dtc_db_path = os.path.join(os.path.dirname(__file__), 'dtc_db.json')

# Carga la base de datos local de DTCs (si existe)
def _cargar_db_dtc() -> Dict[str, Any]:
    try:
        with open(dtc_db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

_DTC_DB = _cargar_db_dtc()

# Conexión OBD-II por WiFi (ELM327)
def _crear_conexion(ip: str = '192.168.0.10', puerto: int = 35000) -> Optional[obd.OBD]:
    try:
        connection = obd.OBD(f"socket://{ip}:{puerto}", fast=False, timeout=5)
        if connection.is_connected():
            return connection
    except Exception:
        pass
    return None

# Decodifica un código DTC de 4 dígitos hex a formato estándar (ej: P0300)
def _decode_dtc(code: str) -> str:
    if len(code) != 4:
        return code
    first = int(code[0], 16)
    dtc_type = ["P", "C", "B", "U"][first >> 2]
    dtc = dtc_type + str(first & 3) + code[1:]
    return dtc

# Parsea la respuesta OBD-II para extraer los códigos DTC
def _parse_dtc_response(response: obd.OBDResponse) -> List[str]:
    if response.is_null() or not response.value:
        return []
    # La librería obd ya decodifica, pero si no, parsear manualmente
    try:
        if hasattr(response, 'value') and isinstance(response.value, list):
            return [str(dtc) for dtc in response.value]
        # Fallback manual
        raw = str(response.value)
        dtcs = []
        for i in range(0, len(raw), 4):
            code = raw[i:i+4]
            if code and code != '0000' and len(code) == 4:
                dtcs.append(_decode_dtc(code))
        return dtcs
    except Exception:
        return []

# Devuelve descripción, sugerencia y PIDs relevantes para un DTC
def resumen_dtc(codigo_dtc: str) -> Dict[str, Any]:
    info = _DTC_DB.get(codigo_dtc.upper())
    if info:
        return {
            "descripcion": info.get("descripcion", "Sin descripción"),
            "sugerencia": info.get("sugerencia", ""),
            "pids_relevantes": info.get("pids_relevantes", [])
        }
    return {
        "descripcion": "Código desconocido",
        "sugerencia": "",
        "pids_relevantes": []
    }

def pids_recomendados_por_dtc(codigo_dtc: str) -> List[str]:
    """Devuelve lista de PIDs sugeridos para un DTC."""
    return resumen_dtc(codigo_dtc).get("pids_relevantes", [])

# Lee DTCs activos (modo 03)
def leer_dtc(ip: str = '192.168.0.10', puerto: int = 35000) -> List[Dict[str, Any]]:
    """Devuelve lista de DTCs activos con descripción y sugerencia."""
    conn = _crear_conexion(ip, puerto)
    if not conn:
        return [{"codigo": None, "descripcion": "Sin conexión OBD-II", "sugerencia": ""}]
    try:
        resp = conn.query(obd.commands['GET_DTC'])
        codigos = _parse_dtc_response(resp)
        resultado = []
        for code in codigos:
            info = resumen_dtc(code)
            resultado.append({
                "codigo": code,
                "descripcion": info["descripcion"],
                "sugerencia": info["sugerencia"]
            })
        if not resultado:
            resultado.append({"codigo": None, "descripcion": "No se encontraron DTCs", "sugerencia": ""})
        return resultado
    except Exception:
        return [{"codigo": None, "descripcion": "Error al leer DTCs", "sugerencia": ""}]
    finally:
        conn.close()

# Lee DTCs pendientes (modo 07)
def leer_dtc_pendientes(ip: str = '192.168.0.10', puerto: int = 35000) -> List[Dict[str, Any]]:
    """Devuelve lista de DTCs pendientes (modo 07)."""
    conn = _crear_conexion(ip, puerto)
    if not conn:
        return [{"codigo": None, "descripcion": "Sin conexión OBD-II", "sugerencia": ""}]
    try:
        cmd = obd.OBDCommand("PENDING_DTC", "Read pending DTCs", "07", 0, lambda x: x)
        resp = conn.query(cmd)
        codigos = _parse_dtc_response(resp)
        resultado = []
        for code in codigos:
            info = resumen_dtc(code)
            resultado.append({
                "codigo": code,
                "descripcion": info["descripcion"],
                "sugerencia": info["sugerencia"]
            })
        if not resultado:
            resultado.append({"codigo": None, "descripcion": "No se encontraron DTCs pendientes", "sugerencia": ""})
        return resultado
    except Exception:
        return [{"codigo": None, "descripcion": "Error al leer DTCs pendientes", "sugerencia": ""}]
    finally:
        conn.close()

# Lee DTCs permanentes (modo 0A)
def leer_dtc_permanentes(ip: str = '192.168.0.10', puerto: int = 35000) -> List[Dict[str, Any]]:
    """Devuelve lista de DTCs permanentes (modo 0A)."""
    conn = _crear_conexion(ip, puerto)
    if not conn:
        return [{"codigo": None, "descripcion": "Sin conexión OBD-II", "sugerencia": ""}]
    try:
        cmd = obd.OBDCommand("PERMANENT_DTC", "Read permanent DTCs", "0A", 0, lambda x: x)
        resp = conn.query(cmd)
        codigos = _parse_dtc_response(resp)
        resultado = []
        for code in codigos:
            info = resumen_dtc(code)
            resultado.append({
                "codigo": code,
                "descripcion": info["descripcion"],
                "sugerencia": info["sugerencia"]
            })
        if not resultado:
            resultado.append({"codigo": None, "descripcion": "No se encontraron DTCs permanentes", "sugerencia": ""})
        return resultado
    except Exception:
        return [{"codigo": None, "descripcion": "Error al leer DTCs permanentes", "sugerencia": ""}]
    finally:
        conn.close()

# Borra los DTCs (modo 04)
def borrar_dtc(ip: str = '192.168.0.10', puerto: int = 35000) -> Dict[str, Any]:
    """Envía comando para borrar los DTCs y confirma resultado."""
    conn = _crear_conexion(ip, puerto)
    if not conn:
        return {"exito": False, "mensaje": "Sin conexión OBD-II"}
    try:
        resp = conn.query(obd.commands['CLEAR_DTC'])
        if resp.is_null():
            return {"exito": False, "mensaje": "No se pudo borrar DTCs"}
        return {"exito": True, "mensaje": "DTCs borrados correctamente"}
    except Exception:
        return {"exito": False, "mensaje": "Error al borrar DTCs"}
    finally:
        conn.close()

# Lee el estado MIL y número de DTCs activos (PID 0101)
def leer_estado_mil(ip: str = '192.168.0.10', puerto: int = 35000) -> Dict[str, Any]:
    """Lee el PID 0101 y retorna si la luz MIL está encendida y el número de DTCs activos."""
    conn = _crear_conexion(ip, puerto)
    if not conn:
        return {"mil": None, "num_dtcs": None, "error": "Sin conexión OBD-II"}
    try:
        cmd = obd.commands['STATUS'] if 'STATUS' in obd.commands else obd.OBDCommand("STATUS", "Status since DTCs cleared", "01 01", 4, lambda x: x)
        resp = conn.query(cmd)
        if resp.is_null() or not resp.value:
            return {"mil": None, "num_dtcs": None, "error": "No se pudo leer estado"}
        # Decodificar respuesta: primer byte, bit 7 = MIL, bits 0-6 = cantidad de DTCs
        val = resp.value
        if hasattr(val, 'value'):
            val = val.value
        if isinstance(val, (list, tuple)) and len(val) > 0:
            byte1 = val[0]
        else:
            # Fallback: intentar parsear string hexadecimal
            try:
                raw = str(resp.value)
                byte1 = int(raw.split()[0], 16)
            except Exception:
                return {"mil": None, "num_dtcs": None, "error": "Respuesta inválida"}
        mil = bool(byte1 & 0x80)
        num_dtcs = byte1 & 0x7F
        return {"mil": mil, "num_dtcs": num_dtcs}
    except Exception:
        return {"mil": None, "num_dtcs": None, "error": "Error al leer estado MIL"}
    finally:
        conn.close()

# Captura los valores de los PIDs durante 'duracion' segundos (1Hz)
def captura_pids(pids: List[str], duracion: int, ip: str = '192.168.0.10', puerto: int = 35000) -> List[Dict[str, Any]]:
    """Captura los valores de los PIDs indicados durante 'duracion' segundos a 1Hz."""
    conn = _crear_conexion(ip, puerto)
    if not conn:
        return [{"error": "Sin conexión OBD-II"}]
    muestras = []
    try:
        for _ in range(duracion):
            muestra = {}
            for pid in pids:
                try:
                    cmd = obd.commands.get(pid) or obd.OBDCommand(pid, pid, pid, 0, lambda x: x)
                    resp = conn.query(cmd)
                    muestra[pid] = resp.value if not resp.is_null() else None
                except Exception:
                    muestra[pid] = None
            muestras.append(muestra)
            time.sleep(1)
        return muestras
    except Exception:
        return [{"error": "Error durante la captura de PIDs"}]
    finally:
        conn.close()
