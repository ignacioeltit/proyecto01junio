import subprocess
import socket
from src.utils.logging_app import log_evento_app

def scan_wifi_networks():
    try:
        result = subprocess.check_output(
            ["netsh", "wlan", "show", "networks"], encoding="utf-8"
        )
        log_evento_app("INFO", "Redes WiFi escaneadas", "wifi_scanner")
        return result
    except Exception as e:
        log_evento_app("ERROR", f"Error escaneando WiFi: {e}", "wifi_scanner")
        return ""

def buscar_elm327_wifi():
    """Alias para buscar_elm327 - mantener compatibilidad"""
    return buscar_elm327()

def buscar_elm327():
    """Buscar dispositivos ELM327 en la red"""
    ips_comunes = ["192.168.0.10", "192.168.4.1", "192.168.1.5"]
    puerto = 35000
    print("🔍 Buscando ELM327 WiFi...")
    for ip in ips_comunes:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((ip, puerto))
            if result == 0:
                print(f"✅ ELM327 encontrado en {ip}:{puerto}")
                sock.close()
                return ip, puerto
            else:
                print(f"❌ No hay respuesta en {ip}:{puerto}")
            sock.close()
        except Exception as e:
            print(f"❌ Error probando {ip}: {e}")
    print("❌ No se encontró ningún ELM327 WiFi")
    return None, None

def diagnostico_red():
    redes = scan_wifi_networks()
    dispositivos = buscar_elm327()
    return {"redes": redes, "elm327": dispositivos}
