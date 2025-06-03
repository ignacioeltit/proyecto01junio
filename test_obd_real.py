import socket
import time

ELM327_IP = "192.168.0.10"
ELM327_PORT = 35000

def send_cmd(sock, cmd):
    print(f"\nEnviando: {cmd.strip()}")
    sock.sendall(cmd.encode())
    time.sleep(1)
    resp = sock.recv(4096)
    print(f"Respuesta: {resp.decode(errors='ignore')}")
    return resp

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    print(f"Conectando a {ELM327_IP}:{ELM327_PORT} ...")
    s.settimeout(5)
    s.connect((ELM327_IP, ELM327_PORT))

    # Handshake ELM327
    send_cmd(s, "ATZ\r")
    send_cmd(s, "ATE0\r")    # Eco off
    send_cmd(s, "ATL0\r")    # Linefeeds off
    send_cmd(s, "ATH0\r")    # Headers off
    send_cmd(s, "ATS0\r")    # Espacios off

    # Identificación de hardware
    send_cmd(s, "ATI\r")

    # Leer RPM (010C) y Velocidad (010D)
    send_cmd(s, "010C\r")
    send_cmd(s, "010D\r")

    print("FIN del test.")
