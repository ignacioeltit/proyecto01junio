import socket
import time
from datetime import datetime
import os

class ELM327_WiFi_Dashboard:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.log_file = None
        
    def connect(self):
        """Conectar al ELM327 WiFi"""
        try:
            print("🔌 Conectando a ELM327 WiFi...")
            
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect(("192.168.0.10", 35000))
            
            # Inicializar ELM327
            init_commands = ["ATZ\r\n", "ATE0\r\n", "ATL0\r\n", "ATS0\r\n", "ATSP0\r\n"]
            for cmd in init_commands:
                print(f"📤 {cmd.strip()}")
                self.sock.send(cmd.encode())
                time.sleep(0.5)
                response = self.sock.recv(1024).decode('utf-8', errors='ignore')
                print(f"📥 {response.strip()}")
            
            self.connected = True
            print("✅ ELM327 WiFi conectado y configurado")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def read_data(self):
        """Leer datos OBD"""
        if not self.connected:
            return None
            
        try:
            data = {}
            
            # RPM (010C)
            self.sock.send(b"010C\r\n")
            time.sleep(0.3)
            response = self.sock.recv(1024).decode('utf-8', errors='ignore')
            data['rpm'] = self.parse_rpm(response)
            
            # Velocidad (010D)
            self.sock.send(b"010D\r\n") 
            time.sleep(0.3)
            response = self.sock.recv(1024).decode('utf-8', errors='ignore')
            data['velocidad'] = self.parse_speed(response)
            
            # Temperatura (0105)
            self.sock.send(b"0105\r\n")
            time.sleep(0.3)
            response = self.sock.recv(1024).decode('utf-8', errors='ignore')
            data['temp_motor'] = self.parse_temp(response)
            
            # Carga del motor (0104)
            self.sock.send(b"0104\r\n")
            time.sleep(0.3)
            response = self.sock.recv(1024).decode('utf-8', errors='ignore')
            data['carga_motor'] = self.parse_load(response)
            
            # Timestamp
            data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            return data
            
        except Exception as e:
            print(f"❌ Error leyendo datos: {e}")
            return None
    
    def parse_rpm(self, response):
        try:
            clean = response.replace(' ', '').replace('\r', '').replace('\n', '').upper()
            if '410C' in clean:
                start = clean.find('410C') + 4
                hex_data = clean[start:start+4]
                if len(hex_data) == 4:
                    rpm = int(hex_data, 16) / 4
                    return int(rpm)
        except:
            pass
        return 0
    
    def parse_speed(self, response):
        try:
            clean = response.replace(' ', '').replace('\r', '').replace('\n', '').upper()
            if '410D' in clean:
                start = clean.find('410D') + 4
                hex_data = clean[start:start+2]
                if len(hex_data) == 2:
                    speed = int(hex_data, 16)
                    return speed
        except:
            pass
        return 0
    
    def parse_temp(self, response):
        try:
            clean = response.replace(' ', '').replace('\r', '').replace('\n', '').upper()
            if '4105' in clean:
                start = clean.find('4105') + 4
                hex_data = clean[start:start+2]
                if len(hex_data) == 2:
                    temp = int(hex_data, 16) - 40
                    return temp
        except:
            pass
        return 0
    
    def parse_load(self, response):
        try:
            clean = response.replace(' ', '').replace('\r', '').replace('\n', '').upper()
            if '4104' in clean:
                start = clean.find('4104') + 4
                hex_data = clean[start:start+2]
                if len(hex_data) == 2:
                    load = (int(hex_data, 16) * 100) / 255
                    return round(load, 1)
        except:
            pass
        return 0
    
    def create_log_file(self):
        """Crear archivo de log"""
        if not os.path.exists("logs_obd"):
            os.makedirs("logs_obd")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs_obd/obd_wifi_log_{timestamp}.csv"
        
        header = "timestamp,rpm,velocidad,temp_motor,carga_motor\n"
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(header)
        
        print(f"📄 Log creado: {self.log_file}")
    
    def log_data(self, data):
        """Guardar datos en log"""
        if self.log_file and data:
            row = f"{data['timestamp']},{data['rpm']},{data['velocidad']},{data['temp_motor']},{data['carga_motor']}\n"
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(row)
    
    def run_dashboard(self):
        """Ejecutar dashboard interactivo"""
        print("\n🚗💨 ELM327 WiFi Dashboard")
        print("=" * 40)
        
        if not self.connect():
            return
        
        print("\n📋 Comandos disponibles:")
        print("1 - Leer datos una vez")
        print("2 - Monitoreo continuo (cada 2 segundos)")
        print("3 - Logging continuo a archivo")
        print("q - Salir")
        
        while True:
            try:
                cmd = input("\n➤ Comando: ").strip().lower()
                
                if cmd == 'q':
                    print("👋 Cerrando dashboard...")
                    break
                
                elif cmd == '1':
                    print("\n📊 Leyendo datos...")
                    data = self.read_data()
                    if data:
                        print(f"🔄 RPM: {data['rpm']}")
                        print(f"🏎️ Velocidad: {data['velocidad']} km/h")
                        print(f"🌡️ Temperatura: {data['temp_motor']}°C")
                        print(f"📊 Carga motor: {data['carga_motor']}%")
                    else:
                        print("❌ No se pudieron leer datos")
                
                elif cmd == '2':
                    print("\n📊 Monitoreo continuo (Ctrl+C para parar)...")
                    try:
                        while True:
                            data = self.read_data()
                            if data:
                                timestamp = data['timestamp'].split('.')[0]
                                print(f"[{timestamp}] RPM:{data['rpm']:4d} | Vel:{data['velocidad']:3d}km/h | Temp:{data['temp_motor']:3d}°C | Carga:{data['carga_motor']:5.1f}%")
                            time.sleep(2)
                    except KeyboardInterrupt:
                        print("\n⏹️ Monitoreo detenido")
                
                elif cmd == '3':
                    self.create_log_file()
                    print(f"\n📝 Logging continuo a {self.log_file}")
                    print("⏹️ Ctrl+C para parar...")
                    try:
                        count = 0
                        while True:
                            data = self.read_data()
                            if data:
                                self.log_data(data)
                                count += 1
                                print(f"📊 Registro #{count}: RPM={data['rpm']}, Vel={data['velocidad']}, Temp={data['temp_motor']}°C")
                            time.sleep(1)
                    except KeyboardInterrupt:
                        print(f"\n✅ Logging detenido. {count} registros guardados en {self.log_file}")
                
                else:
                    print("❌ Comando no válido")
                    
            except KeyboardInterrupt:
                print("\n👋 Saliendo...")
                break
        
        # Cerrar conexión
        if self.sock:
            self.sock.close()
        print("🔌 Conexión cerrada")

if __name__ == "__main__":
    dashboard = ELM327_WiFi_Dashboard()
    dashboard.run_dashboard()