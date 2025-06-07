import time
from datetime import datetime
from dashboard_optimizado_wifi_final import OptimizedELM327Connection, OPERATION_MODES

def main():
    # Crear conexión en modo emulador
    elm = OptimizedELM327Connection()
    elm._mode = OPERATION_MODES["EMULATOR"]
    
    # Conectar
    if elm.connect():
        print("✅ Conectado al dispositivo")
        print("\nLeyendo PIDs en tiempo real...")
        print("-" * 50)
        
        try:
            while True:
                # Leer PIDs rápidos
                fast_data = elm.read_fast_data()
                
                # Leer PIDs lentos
                slow_data = elm.read_slow_data()
                
                # Mostrar timestamp
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')}")
                
                # Mostrar PIDs rápidos
                print("\n📊 PIDs RÁPIDOS:")
                for pid, data in fast_data.items():
                    print(f"{data['name']}: {data['value']} {data['unit']}")
                
                # Mostrar PIDs lentos
                print("\n📊 PIDs LENTOS:")
                for pid, data in slow_data.items():
                    print(f"{data['name']}: {data['value']} {data['unit']}")
                
                print("-" * 50)
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n⚡ Monitoreo detenido por el usuario")
    else:
        print("❌ Error conectando al dispositivo")

if __name__ == "__main__":
    main()
