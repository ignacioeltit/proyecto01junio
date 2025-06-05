import socket
import time

def capturar_pids_y_formato():
    print("🔍 CAPTURANDO PIDs SOPORTADOS Y FORMATO DE RESPUESTAS")
    print("=" * 60)
    
    ip = "192.168.0.10"
    port = 35000
    
    try:
        print(f"📡 Conectando a {ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((ip, port))
        print(f"✅ Conectado exitosamente")
        
        def send_cmd(cmd, wait_time=1):
            print(f"📤 Enviando: {cmd}")
            sock.sendall(f"{cmd}\r\n".encode())
            time.sleep(wait_time)
            response = sock.recv(2048).decode('utf-8', errors='ignore')
            print(f"📥 Respuesta: '{response.strip()}'")
            return response.strip()
        
        print("\n🔧 INICIALIZANDO ELM327...")
        send_cmd("ATZ", 3)
        send_cmd("ATI", 1)
        send_cmd("ATE0", 1)
        send_cmd("ATSP0", 1)
        
        print("\n🔍 VERIFICANDO CONEXIÓN CON VEHÍCULO...")
        voltage_resp = send_cmd("ATRV", 1)
        basic_test = send_cmd("0100", 2)
        
        print("\n📋 FASE 1: CAPTURANDO PIDs SOPORTADOS")
        
        pids_groups = [
            ("0100", "PIDs 01-20"),
            ("0120", "PIDs 21-40"), 
            ("0140", "PIDs 41-60")
        ]
        
        all_supported_pids = []
        
        for pid_cmd, description in pids_groups:
            print(f"\n🔍 {description} - Comando: {pid_cmd}")
            response = send_cmd(pid_cmd, 2)
            
            clean_resp = response.replace('\r', '').replace('\n', '').replace('>', '').strip()
            
            if "41" in clean_resp and len(clean_resp) > 10:
                print(f"   ✅ Respuesta válida: {clean_resp}")
                
                parts = clean_resp.split()
                if len(parts) >= 6:
                    hex_bytes = parts[2:6]
                    print(f"   📈 Bytes HEX: {' '.join(hex_bytes)}")
                    
                    supported_list = []
                    base_pid = int(pid_cmd[2:4], 16)
                    
                    for i, hex_byte in enumerate(hex_bytes):
                        try:
                            byte_val = int(hex_byte, 16)
                            for bit in range(8):
                                if byte_val & (1 << (7-bit)):
                                    pid_num = base_pid + (i * 8) + bit + 1
                                    pid_hex = f"01{pid_num:02X}"
                                    supported_list.append(pid_hex)
                        except ValueError:
                            pass
                    
                    print(f"   ✅ PIDs encontrados: {len(supported_list)}")
                    print(f"   📋 Lista: {supported_list}")
                    all_supported_pids.extend(supported_list)
            else:
                print(f"   ❌ Sin datos válidos")
        
        print("\n\n📊 FASE 2: PROBANDO PIDs INDIVIDUALES")
        
        test_pids = [
            ("010C", "RPM del motor"),
            ("010D", "Velocidad del vehículo"),
            ("0105", "Temperatura refrigerante"),
            ("010F", "Temperatura aire admisión"),
            ("0111", "Posición acelerador"),
            ("0110", "Flujo de aire MAF"),
            ("012F", "Nivel de combustible"),
            ("0142", "Voltaje módulo control"),
            ("0104", "Carga calculada del motor")
        ]
        
        working_pids = []
        pid_data = {}
        
        for pid, description in test_pids:
            print(f"\n🔍 Probando {pid}: {description}")
            
            response = send_cmd(pid, 1)
            clean_resp = response.replace('\r', '').replace('\n', '').replace('>', '').strip()
            
            print(f"   📥 Respuesta: '{clean_resp}'")
            
            if "41" in clean_resp and "NO DATA" not in clean_resp and "STOPPED" not in clean_resp:
                print(f"   ✅ DATOS VÁLIDOS")
                
                parts = clean_resp.split()
                if len(parts) >= 3:
                    data_bytes = parts[2:]
                    print(f"   📊 Bytes: {' '.join(data_bytes)}")
                    
                    interpreted_value = None
                    
                    if pid == "010C" and len(data_bytes) >= 2:
                        try:
                            a = int(data_bytes[0], 16)
                            b = int(data_bytes[1], 16)
                            rpm = ((a * 256) + b) / 4
                            interpreted_value = f"{rpm} RPM"
                            print(f"   🔧 RPM: {rpm}")
                        except:
                            pass
                    
                    elif pid == "010D" and len(data_bytes) >= 1:
                        try:
                            speed = int(data_bytes[0], 16)
                            interpreted_value = f"{speed} km/h"
                            print(f"   🚗 Velocidad: {speed} km/h")
                        except:
                            pass
                    
                    elif pid == "0105" and len(data_bytes) >= 1:
                        try:
                            temp = int(data_bytes[0], 16) - 40
                            interpreted_value = f"{temp}°C"
                            print(f"   🌡️ Temperatura: {temp}°C")
                        except:
                            pass
                
                working_pids.append(pid)
                pid_data[pid] = {
                    'description': description,
                    'response': clean_resp,
                    'bytes': data_bytes,
                    'value': interpreted_value
                }
                
            else:
                print(f"   ❌ SIN DATOS")
        
        print("\n\n📊 RESUMEN FINAL")
        print("=" * 50)
        
        print(f"\n✅ PIDs SOPORTADOS: {len(all_supported_pids)}")
        print(f"✅ PIDs FUNCIONALES: {len(working_pids)}")
        
        print(f"\nPIDs con datos reales:")
        for pid in working_pids:
            info = pid_data[pid]
            print(f"   {pid}: {info['description']} → {info['value']}")
        
        sock.close()
        
        # Guardar resultados
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"pids_capturados_{timestamp}.txt"
        
        with open(filename, "w", encoding='utf-8') as f:
            f.write("CAPTURA PIDs ELM327\n")
            f.write("=" * 30 + "\n")
            f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"PIDs FUNCIONALES: {working_pids}\n\n")
            
            f.write("DETALLES:\n")
            for pid in working_pids:
                info = pid_data[pid]
                f.write(f"{pid}: {info['description']}\n")
                f.write(f"  Valor: {info['value']}\n")
                f.write(f"  Respuesta: {info['response']}\n\n")
        
        print(f"\n💾 Guardado en: {filename}")
        
        return working_pids
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return None

if __name__ == "__main__":
    print("🚗 Motor encendido y cable OBD conectado")
    input("📍 Presiona ENTER para comenzar...")
    
    result = capturar_pids_y_formato()
    
    if result:
        print(f"\n🎉 ¡ÉXITO! {len(result)} PIDs funcionales")
    else:
        print("\n❌ Error en captura")
