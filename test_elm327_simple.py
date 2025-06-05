import socket
import time

def test_elm327_wifi():
    print("🔌 Conectando a ELM327 WiFi...")
    
    try:
        # Conectar al ELM327
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("192.168.0.10", 35000))
        
        print("✅ ¡Conectado exitosamente!")
        
        # Enviar comandos de inicialización
        commands = ["ATZ\r\n", "ATE0\r\n", "ATL0\r\n", "ATS0\r\n"]
        
        for cmd in commands:
            print(f"📤 Enviando: {cmd.strip()}")
            sock.send(cmd.encode())
            time.sleep(0.5)
            response = sock.recv(1024).decode('utf-8', errors='ignore')
            print(f"📥 Respuesta: {response.strip()}")
        
        # Probar comando OBD (RPM)
        print("\n🔧 Probando comando OBD...")
        sock.send(b"010C\r\n")  # Comando para RPM
        time.sleep(0.5)
        response = sock.recv(1024).decode('utf-8', errors='ignore')
        print(f"📊 RPM respuesta: {response.strip()}")
        
        sock.close()
        print("✅ Test completado exitosamente")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_elm327_wifi()