import socket
import time

def test_elm327_direct():
    print("🔌 PRUEBA DIRECTA ELM327 WiFi")
    print("===============================")
    
    ip = "192.168.0.10"
    port = 35000
    
    try:
        # Crear conexión
        print(f"📡 Conectando a {ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, port))
        print("✅ Conexión TCP establecida")
        
        # Comandos de prueba
        commands = [
            ("ATZ", "Reset ELM327"),
            ("ATI", "Información del dispositivo"),
            ("ATE0", "Desactivar eco"),
            ("ATSP0", "Protocolo automático"),
            ("0100", "PIDs soportados"),
            ("010C", "RPM del motor"),
            ("010D", "Velocidad"),
            ("0105", "Temperatura refrigerante")
        ]
        
        for cmd, desc in commands:
            print(f"\n📤 Enviando: {cmd} ({desc})")
            
            # Enviar comando
            sock.sendall(f"{cmd}\r\n".encode())
            time.sleep(1)
            
            # Leer respuesta
            response = sock.recv(1024).decode('utf-8', errors='ignore')
            clean_response = response.replace('\r', '').replace('\n', '').replace('>', '').strip()
            
            print(f"📥 Respuesta: {clean_response}")
            
            # Analizar respuesta
            if 'ERROR' in clean_response:
                print("❌ Error en comando")
            elif len(clean_response) > 0:
                print("✅ Comando exitoso")
                
                # Parsear datos específicos
                if cmd == "010C" and len(clean_response) >= 6:
                    try:
                        hex_data = clean_response[-4:]
                        rpm = int(hex_data, 16) // 4
                        print(f"🔧 RPM calculado: {rpm}")
                    except:
                        print("⚠️ No se pudo parsear RPM")
                        
                elif cmd == "010D" and len(clean_response) >= 4:
                    try:
                        hex_data = clean_response[-2:]
                        speed = int(hex_data, 16)
                        print(f"🚗 Velocidad calculada: {speed} km/h")
                    except:
                        print("⚠️ No se pudo parsear velocidad")
            else:
                print("⚠️ Sin respuesta")
            
            time.sleep(0.5)
        
        sock.close()
        print("\n✅ Prueba completada - Conexión cerrada")
        
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    test_elm327_direct()
