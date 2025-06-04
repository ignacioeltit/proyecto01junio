import socket
import time

ELM327_IP = "192.168.0.10"   # Cambia por la IP real de tu ELM327 WiFi
ELM327_PORT = 35000          # Puerto estándar

def send_cmd(sock, cmd):
    sock.sendall(cmd.encode())
    time.sleep(0.3)
    resp = sock.recv(4096)
    return resp.decode(errors="ignore")

def decode_bitmask(cmd, response):
    # Extrae solo la respuesta con '41xx' y convierte la bitmask a lista de PIDs
    lines = [l.strip() for l in response.splitlines() if l.strip().startswith("41")]
    if not lines: return []
    hex_mask = ''.join(lines[0][4:]).replace(" ", "")
    if len(hex_mask) < 8: return []
    mask = int(hex_mask[:8], 16)
    base_pid = int(cmd[2:], 16)
    pids = []
    for i in range(32):
        if mask & (1 << (31 - i)):
            pids.append("01%02X" % (base_pid + i + 1))
    return pids

if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        print(f"Conectando a {ELM327_IP}:{ELM327_PORT} ...")
        s.connect((ELM327_IP, ELM327_PORT))
        print(send_cmd(s, "ATZ\r"))
        print(send_cmd(s, "ATE0\r"))
        print(send_cmd(s, "ATL0\r"))
        print(send_cmd(s, "ATH0\r"))
        print(send_cmd(s, "ATS0\r"))
        print("---- Escaneando PIDs soportados (Modo 01) ----")
        all_pids = []
        for cmd in ["0100", "0120", "0140", "0160", "0180", "01A0", "01C0", "01E0"]:
            print(f"> {cmd}")
            resp = send_cmd(s, cmd + "\r")
            found = decode_bitmask(cmd, resp)
            print(f"PIDs soportados en {cmd}: {found}")
            all_pids.extend(found)
        print("\n=== PIDs Soportados en el vehículo ===")
        for pid in sorted(set(all_pids)):
            print(pid)
