"""
Test mínimo de conexión y adquisición OBD-II real.
Conecta al ELM327, envía 010C (RPM) y 010D (velocidad), muestra respuesta cruda y parseada.
"""
import sys
import os
from obd.connection import OBDConnection
from obd.elm327 import ELM327
from obd.pids import PIDS
from obd.pids_ext import normalizar_pid

def main():
    ip = "192.168.0.10"
    port = 35000
    print(f"Conectando a ELM327 en {ip}:{port} ...")
    conn = OBDConnection(mode="wifi", ip=ip, tcp_port=port)
    conn.connect()
    elm = ELM327(conn)
    handshake = elm.initialize()
    print(f"Handshake: {'OK' if handshake else 'FALLO'}")
    for pid, nombre in [("010C", "rpm"), ("010D", "vel")]:
        cmd = PIDS[pid]["cmd"]
        print(f"Enviando comando {cmd} para {nombre} ...")
        try:
            resp = elm.send_pid(cmd)
            print(f"Respuesta cruda para {cmd}: {resp}")
            # Parsing básico
            if pid == "010C" and resp and "41 0C" in resp:
                idx = resp.find("41 0C")
                hexdata = resp[idx+5:idx+10].replace(" ","")
                if len(hexdata) == 4:
                    A = int(hexdata[:2], 16)
                    B = int(hexdata[2:], 16)
                    rpm = ((A*256)+B)//4
                    print(f"RPM parseado: {rpm}")
            elif pid == "010D" and resp and "41 0D" in resp:
                idx = resp.find("41 0D")
                hexdata = resp[idx+5:idx+7].replace(" ","")
                if len(hexdata) == 2:
                    vel = int(hexdata, 16)
                    print(f"Velocidad parseada: {vel}")
        except Exception as e:
            print(f"Error al enviar/parsear {cmd}: {e}")
    conn.close()
    print("Conexión cerrada.")

if __name__ == "__main__":
    main()
