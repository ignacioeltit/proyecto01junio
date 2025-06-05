import socket
import time

def probar_todos_los_pids():
    print("🔍 PROBANDO TODOS LOS PIDs SOPORTADOS")
    print("=" * 60)
    
    ip = "192.168.0.10"
    port = 35000
    
    try:
        print(f"📡 Conectando a {ip}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((ip, port))
        print("✅ Conectado")
        
        def send_cmd(cmd, wait_time=1):
            sock.sendall(f"{cmd}\r\n".encode())
            time.sleep(wait_time)
            response = sock.recv(2048).decode('utf-8', errors='ignore')
            return response.strip()
        
        # Inicializar
        print("\n🔧 Inicializando ELM327...")
        send_cmd("ATZ", 3)
        send_cmd("ATE0", 1)
        send_cmd("ATSP0", 1)
        
        # Lista completa de PIDs encontrados anteriormente
        all_supported_pids = [
            '0101', '0103', '0104', '0105', '0106', '0107', '0108', '0109', 
            '010B', '010C', '010D', '010E', '010F', '0111', '0113', '0114', 
            '0115', '0118', '0119', '011C', '011F', '0120', '0121', '012E', 
            '012F', '0130', '0131', '0133', '013C', '013D', '0140', '0141', 
            '0142', '0143', '0144', '0145', '0146', '0147', '0149', '014A', 
            '014C', '0151'
        ]
        
        print(f"\n📋 PROBANDO {len(all_supported_pids)} PIDs SOPORTADOS:")
        print("-" * 50)
        
        working_pids = []
        all_responses = {}
        
        for i, pid in enumerate(all_supported_pids):
            print(f"\n[{i+1}/{len(all_supported_pids)}] 🔍 Probando {pid}")
            
            response = send_cmd(pid, 0.8)
            clean_resp = response.replace('\r', '').replace('\n', '').replace('>', '').strip()
            
            if "41" in clean_resp and "NO DATA" not in clean_resp and "STOPPED" not in clean_resp:
                print(f"   ✅ FUNCIONAL: {clean_resp}")
                
                # Extraer bytes de datos
                parts = clean_resp.split()
                if len(parts) >= 3:
                    pid_echo = parts[1] if len(parts) > 1 else ""
                    data_bytes = []
                    
                    # Buscar datos después del PID echo
                    for j, part in enumerate(parts[2:], 2):
                        if len(part) == 2 and part != pid_echo:
                            try:
                                int(part, 16)  # Verificar que es hex válido
                                data_bytes.append(part)
                            except ValueError:
                                break
                        elif part == "41":  # Nueva respuesta empezando
                            break
                    
                    print(f"   📊 Datos: {' '.join(data_bytes)}")
                    
                    # Interpretar datos conocidos
                    interpreted = interpretar_pid(pid, data_bytes)
                    if interpreted:
                        print(f"   🎯 Valor: {interpreted}")
                    
                    working_pids.append(pid)
                    all_responses[pid] = {
                        'response': clean_resp,
                        'data_bytes': data_bytes,
                        'interpreted': interpreted
                    }
            else:
                print(f"   ❌ Sin datos: {clean_resp}")
                all_responses[pid] = {
                    'response': clean_resp,
                    'data_bytes': [],
                    'interpreted': None
                }
        
        print(f"\n\n📊 RESUMEN COMPLETO:")
        print("=" * 50)
        print(f"✅ PIDs probados: {len(all_supported_pids)}")
        print(f"✅ PIDs funcionales: {len(working_pids)}")
        print(f"❌ PIDs sin datos: {len(all_supported_pids) - len(working_pids)}")
        
        print(f"\n🎯 PIDs FUNCIONALES CON DATOS:")
        for pid in working_pids:
            info = all_responses[pid]
            interpreted = info['interpreted'] or 'Sin interpretar'
            print(f"   {pid}: {interpreted}")
        
        sock.close()
        
        # Guardar resultados completos
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"todos_pids_probados_{timestamp}.txt"
        
        with open(filename, "w", encoding='utf-8') as f:
            f.write("PRUEBA COMPLETA DE TODOS LOS PIDs SOPORTADOS\n")
            f.write("=" * 60 + "\n")
            f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total PIDs probados: {len(all_supported_pids)}\n")
            f.write(f"PIDs funcionales: {len(working_pids)}\n\n")
            
            f.write("PIDs FUNCIONALES:\n")
            f.write("-" * 20 + "\n")
            for pid in working_pids:
                info = all_responses[pid]
                f.write(f"{pid}: {info['interpreted'] or 'Sin interpretar'}\n")
                f.write(f"  Respuesta: {info['response']}\n")
                f.write(f"  Bytes: {' '.join(info['data_bytes'])}\n\n")
            
            f.write("PIDs SIN DATOS:\n")
            f.write("-" * 15 + "\n")
            for pid, info in all_responses.items():
                if pid not in working_pids:
                    f.write(f"{pid}: {info['response']}\n")
        
        print(f"\n💾 Resultados completos en: {filename}")
        
        return working_pids, all_responses
        
    except Exception as e:
        print(f"💥 Error: {e}")
        return None, None

def interpretar_pid(pid, data_bytes):
    """Interpretar PIDs conocidos"""
    try:
        if pid == "010C" and len(data_bytes) >= 2:  # RPM
            a = int(data_bytes[0], 16)
            b = int(data_bytes[1], 16)
            rpm = ((a * 256) + b) / 4
            return f"{rpm} RPM"
        
        elif pid == "010D" and len(data_bytes) >= 1:  # Velocidad
            speed = int(data_bytes[0], 16)
            return f"{speed} km/h"
        
        elif pid == "0105" and len(data_bytes) >= 1:  # Temperatura refrigerante
            temp = int(data_bytes[0], 16) - 40
            return f"{temp}°C (Refrigerante)"
        
        elif pid == "010F" and len(data_bytes) >= 1:  # Temperatura admisión
            temp = int(data_bytes[0], 16) - 40
            return f"{temp}°C (Admisión)"
        
        elif pid == "0111" and len(data_bytes) >= 1:  # Posición acelerador
            throttle = int(data_bytes[0], 16) * 100 / 255
            return f"{throttle:.1f}% (Acelerador)"
        
        elif pid == "0104" and len(data_bytes) >= 1:  # Carga motor
            load = int(data_bytes[0], 16) * 100 / 255
            return f"{load:.1f}% (Carga motor)"
        
        elif pid == "012F" and len(data_bytes) >= 1:  # Nivel combustible
            fuel = int(data_bytes[0], 16) * 100 / 255
            return f"{fuel:.1f}% (Combustible)"
        
        elif pid == "0142" and len(data_bytes) >= 2:  # Voltaje
            a = int(data_bytes[0], 16)
            b = int(data_bytes[1], 16)
            voltage = ((a * 256) + b) / 1000
            return f"{voltage:.2f}V (Módulo)"
        
        elif pid == "010B" and len(data_bytes) >= 1:  # Presión colector
            pressure = int(data_bytes[0], 16)
            return f"{pressure} kPa (Colector)"
        
        elif pid == "010A" and len(data_bytes) >= 1:  # Presión combustible
            pressure = int(data_bytes[0], 16) * 3
            return f"{pressure} kPa (Combustible)"
        
        else:
            return f"Datos: {' '.join(data_bytes)}"
            
    except:
        return None

if __name__ == "__main__":
    print("🚗 IMPORTANTE: Motor encendido y cable OBD conectado")
    print("⏱️ Este proceso probará TODOS los 42 PIDs soportados")
    print("🕐 Tiempo estimado: 3-4 minutos")
    print()
    
    input("📍 Presiona ENTER para probar TODOS los PIDs...")
    
    working_pids, all_responses = probar_todos_los_pids()
    
    if working_pids:
        print(f"\n🎉 ¡ÉXITO TOTAL!")
        print(f"📊 {len(working_pids)} PIDs funcionales de 42 soportados")
        print("🔥 ¡Ahora tenemos datos completos para el dashboard!")
    else:
        print("\n❌ Error en la prueba")
