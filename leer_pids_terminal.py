import time
from dashboard_optimizado_wifi_final import OptimizedELM327Connection, OPERATION_MODES

def main():
    # Crear instancia del dispositivo en modo emulador
    elm = OptimizedELM327Connection()
    elm._mode = OPERATION_MODES["EMULATOR"]
    
    print("Conectando dispositivo...")
    if elm.connect():
        print("✅ Dispositivo conectado en modo emulador")
        
        print("\nLeyendo PIDs en tiempo real (presiona Ctrl+C para detener)...")
        print("=" * 60)
        
        try:
            while True:
                # Leer datos rápidos
                fast_data = elm.read_fast_data()
                print("\n📊 DATOS CRÍTICOS:")
                for pid, data in fast_data.items():
                    print(f"{data['name']}: {data['value']} {data['unit']}")
                
                # Leer datos lentos
                slow_data = elm.read_slow_data()
                print("\n📊 DATOS SECUNDARIOS:")
                for pid, data in slow_data.items():
                    print(f"{data['name']}: {data['value']} {data['unit']}")
                
                print("\n" + "=" * 60)
                time.sleep(0.5)  # Actualizar cada 500ms
                
        except KeyboardInterrupt:
            print("\n⚡ Monitoreo detenido")
            elm.disconnect()
    else:
        print("❌ Error conectando dispositivo")

if __name__ == "__main__":
    main()
