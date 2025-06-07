from dashboard_optimizado_wifi_final import OptimizedELM327Connection

# Crear conexión en modo emulador
elm = OptimizedELM327Connection()
elm._mode = "emulator"

# Conectar
if elm.connect():
    print("✅ Conectado en modo emulador")
    
    # Leer PIDs rápidos
    fast_data = elm.read_fast_data()
    
    # Mostrar PIDs rápidos
    print("\n📊 PIDs CRÍTICOS:")
    for pid, data in fast_data.items():
        print(f"{data['name']}: {data['value']} {data['unit']}")
    
    # Leer PIDs lentos  
    slow_data = elm.read_slow_data()
    
    # Mostrar PIDs lentos
    print("\n📊 PIDs SECUNDARIOS:")
    for pid, data in slow_data.items():
        print(f"{data['name']}: {data['value']} {data['unit']}")
else:
    print("❌ Error conectando al dispositivo")
