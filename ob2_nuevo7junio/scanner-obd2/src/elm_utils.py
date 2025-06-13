import socket
import time
import re

class Elm327WiFi:
    def __init__(self, ip="192.168.0.10", port=35000, timeout=1.0):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.conn = None
        self.protocol_map = {
            "1": "SAE J1850 PWM",
            "2": "SAE J1850 VPW",
            "3": "ISO 9141-2",
            "4": "ISO 14230-4 KWP (5 baud init)",
            "5": "ISO 14230-4 KWP (fast init)",
            "6": "ISO 15765-4 CAN (11bit, 500kbps)",
            "7": "ISO 15765-4 CAN (29bit, 500kbps)",
            "8": "ISO 15765-4 CAN (11bit, 250kbps)",
            "9": "ISO 15765-4 CAN (29bit, 250kbps)",
            "A": "SAE J1939 CAN (29bit, 250kbps)",
            "B": "USER1 CAN",
            "C": "USER2 CAN"
        }

    def connect(self):
        self.conn = socket.create_connection((self.ip, self.port), timeout=self.timeout)
        self.conn.settimeout(self.timeout)
        self.flush()
        self.send_command("AT Z")
        self.send_command("AT E0")  # Echo off
        self.send_command("AT S0")  # Spaces off
        self.send_command("AT L0")  # Linefeeds off
        self.send_command("AT H0")  # Headers off

    def flush(self):
        try:
            self.conn.recv(1024)
        except:
            pass

    def send_command(self, cmd):
        self.conn.sendall((cmd.strip() + "\r").encode())
        time.sleep(0.3)
        try:
            response = self.conn.recv(1024).decode(errors="ignore")
            return response.strip().replace(">", "")
        except socket.timeout:
            return ""

    def scan_protocols(self):
        self.connect()
        working_protocol = None
        for code in list("123456789ABC"):
            self.send_command(f"AT SP {code}")
            response = self.send_command("0100")
            if "41 00" in response or ("NO DATA" not in response and "?" not in response and response.strip()):
                working_protocol = code
                break
        if working_protocol:
            return working_protocol, self.protocol_map.get(working_protocol, "Desconocido")
        else:
            return None, "No se detectó protocolo compatible"

    def read_vin(self):
        self.connect()
        self.send_command("AT SP 0")  # Auto protocolo si aún no definido
        response = self.send_command("09 02")
        hex_bytes = re.findall(r'[0-9A-Fa-f]{2}', response)
        vin_bytes = []
        skip = 0
        for b in hex_bytes:
            if skip < 3:
                skip += 1
                continue
            vin_bytes.append(b)
            if len(vin_bytes) >= 17:
                break
        vin = ''.join(chr(int(b, 16)) for b in vin_bytes if int(b, 16) >= 32)
        return vin if vin else "VIN no detectado"

    def scan_supported_pids(self):
        self.connect()
        supported_pids = []
        pid_groups = ["0100", "0120", "0140", "0160", "0180", "01A0", "01C0"]

        for group in pid_groups:
            response = self.send_command(group)
            if not response or "NO DATA" in response or "?" in response:
                break
            try:
                hex_data = ''.join(re.findall(r'[0-9A-Fa-f]{2}', response)[2:])  # Omitir 41 XX
                binary = bin(int(hex_data, 16))[2:].zfill(len(hex_data) * 4)
                base = int(group[-2:], 16)
                for i, bit in enumerate(binary):
                    if bit == "1":
                        pid = base + i + 1
                        supported_pids.append(f"{pid:02X}")
            except:
                continue
        return supported_pids
