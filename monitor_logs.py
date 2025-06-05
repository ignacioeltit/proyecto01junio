# Crear: monitor_logs.py
import os
import time
from datetime import datetime

def monitor_logs_real_time():
    print("👁️ MONITOR DE LOGS EN TIEMPO REAL")
    print("=" * 40)
    
    log_dir = "logs_obd"
    
    if not os.path.exists(log_dir):
        print("❌ Carpeta logs_obd no existe")
        return
    
    print("🔍 Monitoreando carpeta logs_obd...")
    print("📋 Presiona Ctrl+C para detener")
    print("-" * 40)
    
    last_files = set()
    last_sizes = {}
    
    try:
        while True:
            current_files = set()
            for file in os.listdir(log_dir):
                if file.endswith('.csv'):
                    current_files.add(file)
            
            # Detectar archivos nuevos
            new_files = current_files - last_files
            for new_file in new_files:
                print(f"📝 NUEVO ARCHIVO: {new_file}")
                last_sizes[new_file] = 0
            
            # Verificar cambios de tamaño
            for file in current_files:
                filepath = os.path.join(log_dir, file)
                current_size = os.path.getsize(filepath)
                
                if file not in last_sizes:
                    last_sizes[file] = current_size
                elif current_size != last_sizes[file]:
                    size_mb = current_size / 1024 / 1024
                    added_bytes = current_size - last_sizes[file]
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] 📊 {file}: {size_mb:.3f}MB (+{added_bytes} bytes)")
                    
                    last_sizes[file] = current_size
                    
                    # Mostrar último dato si existe
                    if current_size > 100:
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                if len(lines) > 1:
                                    last_line = lines[-1].strip()
                                    parts = last_line.split(',')
                                    if len(parts) >= 4:
                                        rpm = parts[1] if len(parts) > 1 else 'N/A'
                                        vel = parts[2] if len(parts) > 2 else 'N/A'
                                        temp = parts[3] if len(parts) > 3 else 'N/A'
                                        print(f"           ➤ RPM={rpm}, Vel={vel}, Temp={temp}°C")
                        except:
                            pass
            
            last_files = current_files
            time.sleep(2)
            
    except KeyboardInterrupt:
        print(f"\n✅ Monitoreo detenido")
        
        print(f"\n📊 RESUMEN FINAL:")
        for file in current_files:
            filepath = os.path.join(log_dir, file)
            size_mb = os.path.getsize(filepath) / 1024 / 1024
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                records = max(0, lines - 1)
                print(f"   📄 {file}: {records} registros, {size_mb:.3f}MB")
            except:
                print(f"   📄 {file}: Error leyendo archivo")

if __name__ == "__main__":
    monitor_logs_real_time()