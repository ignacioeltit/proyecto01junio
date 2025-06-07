import time
import random

def simular_pids():
    """Simula la lectura de PIDs OBD-II"""
    while True:
        print("\n=== DATOS EN TIEMPO REAL ===")
        print("\nPIDs CRÍTICOS:")
        print(f"RPM: {800 + random.randint(-50, 50)} RPM")
        print(f"Velocidad: {60 + random.randint(-5, 5)} km/h")
        print(f"Temperatura Motor: {85 + random.randint(-2, 2)} °C")
        print(f"Carga Motor: {20 + random.randint(-5, 5)} %")
        print(f"Posición Acelerador: {15 + random.randint(-3, 3)} %")
        
        print("\nPIDs SECUNDARIOS:")
        print(f"Temperatura Admisión: {25 + random.randint(-2, 2)} °C")
        print(f"Nivel Combustible: {75 + random.randint(-5, 5)} %")
        print(f"Voltaje: {12.5 + random.uniform(-0.2, 0.2):.1f} V")
        print(f"Presión MAP: {100 + random.randint(-10, 10)} kPa")
        
        print("\nPresiona Ctrl+C para detener...")
        time.sleep(1)

if __name__ == "__main__":
    try:
        simular_pids()
    except KeyboardInterrupt:
        print("\nMonitoreo detenido por el usuario")
