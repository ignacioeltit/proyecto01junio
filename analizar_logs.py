import os
import csv
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import glob

def analizar_logs_obd():
    print("📊 ANALIZADOR DE LOGS OBD-II")
    print("=" * 50)
    
    # Buscar archivos de log
    log_dir = "logs_obd"
    if not os.path.exists(log_dir):
        print("❌ Carpeta logs_obd no encontrada")
        return
    
    log_files = glob.glob(os.path.join(log_dir, "*.csv"))
    if not log_files:
        print("❌ No se encontraron archivos de log CSV")
        return
    
    # Listar archivos encontrados
    print(f"📁 Encontrados {len(log_files)} archivos de log:")
    for i, file in enumerate(log_files, 1):
        size_mb = os.path.getsize(file) / 1024 / 1024
        mod_time = datetime.fromtimestamp(os.path.getmtime(file))
        print(f"   {i}. {os.path.basename(file)} ({size_mb:.2f}MB) - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Analizar el archivo más reciente
    latest_file = max(log_files, key=os.path.getmtime)
    print(f"\n🔍 Analizando archivo más reciente:")
    print(f"   📄 {os.path.basename(latest_file)}")
    
    try:
        # Leer datos
        df = pd.read_csv(latest_file)
        print(f"   📊 Registros: {len(df)}")
        print(f"   📅 Período: {df['timestamp'].iloc[0]} → {df['timestamp'].iloc[-1]}")
        
        # Estadísticas básicas
        print(f"\n📈 ESTADÍSTICAS BÁSICAS:")
        print("-" * 30)
        
        numeric_columns = ['rpm', 'velocidad', 'temp_motor', 'carga_motor', 'acelerador']
        
        for col in numeric_columns:
            if col in df.columns:
                data = pd.to_numeric(df[col], errors='coerce')
                data = data.dropna()
                
                if len(data) > 0:
                    print(f"   {col.upper()}:")
                    print(f"      Promedio: {data.mean():.1f}")
                    print(f"      Mínimo: {data.min():.1f}")
                    print(f"      Máximo: {data.max():.1f}")
                    print(f"      Registros válidos: {len(data)}/{len(df)}")
        
        # Análisis de calidad de datos
        print(f"\n🔍 CALIDAD DE DATOS:")
        print("-" * 25)
        
        total_records = len(df)
        for col in df.columns:
            if col != 'timestamp':
                valid_data = pd.to_numeric(df[col], errors='coerce').dropna()
                valid_percent = (len(valid_data) / total_records) * 100
                print(f"   {col}: {valid_percent:.1f}% válidos ({len(valid_data)}/{total_records})")
        
        # Detectar patrones interesantes
        print(f"\n🎯 PATRONES DETECTADOS:")
        print("-" * 25)
        
        # RPM
        if 'rpm' in df.columns:
            rpm_data = pd.to_numeric(df['rpm'], errors='coerce').dropna()
            if len(rpm_data) > 0:
                rpm_changes = abs(rpm_data.diff()).dropna()
                big_changes = rpm_changes[rpm_changes > 200]
                print(f"   🔧 RPM: {len(big_changes)} cambios grandes (>200 RPM)")
                if len(big_changes) > 0:
                    print(f"      Mayor cambio: {rpm_changes.max():.0f} RPM")
        
        # Velocidad
        if 'velocidad' in df.columns:
            vel_data = pd.to_numeric(df['velocidad'], errors='coerce').dropna()
            if len(vel_data) > 0:
                moving = vel_data[vel_data > 0]
                print(f"   🚗 Velocidad: {len(moving)} registros en movimiento")
                if len(moving) > 0:
                    print(f"      Velocidad máxima: {vel_data.max():.0f} km/h")
        
        # Temperatura
        if 'temp_motor' in df.columns:
            temp_data = pd.to_numeric(df['temp_motor'], errors='coerce').dropna()
            if len(temp_data) > 0:
                temp_range = temp_data.max() - temp_data.min()
                print(f"   🌡️ Temperatura: Rango de {temp_range:.1f}°C ({temp_data.min():.1f}°C - {temp_data.max():.1f}°C)")
        
        # Análisis temporal
        print(f"\n⏱️ ANÁLISIS TEMPORAL:")
        print("-" * 22)
        
        if len(df) > 1:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            time_diffs = df['timestamp'].diff().dropna()
            avg_interval = time_diffs.mean().total_seconds()
            frequency = 1 / avg_interval if avg_interval > 0 else 0
            
            print(f"   📏 Intervalo promedio: {avg_interval:.2f} segundos")
            print(f"   📊 Frecuencia: {frequency:.2f} Hz")
            print(f"   ⏰ Duración total: {(df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds():.1f} segundos")
        
        # Mostrar últimos registros
        print(f"\n📋 ÚLTIMOS 5 REGISTROS:")
        print("-" * 25)
        
        last_records = df.tail(5)
        for idx, row in last_records.iterrows():
            timestamp = row['timestamp']
            rpm = row.get('rpm', 'N/A')
            vel = row.get('velocidad', 'N/A')
            temp = row.get('temp_motor', 'N/A')
            print(f"   {timestamp} | RPM: {rpm} | Vel: {vel} | Temp: {temp}°C")
        
        # Resumen de archivos
        print(f"\n📁 RESUMEN DE TODOS LOS ARCHIVOS:")
        print("-" * 35)
        
        total_size = 0
        total_records = 0
        
        for file in log_files:
            try:
                file_df = pd.read_csv(file)
                size_mb = os.path.getsize(file) / 1024 / 1024
                total_size += size_mb
                total_records += len(file_df)
                
                print(f"   📄 {os.path.basename(file)}: {len(file_df)} registros, {size_mb:.2f}MB")
            except:
                print(f"   ❌ Error leyendo {os.path.basename(file)}")
        
        print(f"\n📊 TOTALES:")
        print(f"   📁 Archivos: {len(log_files)}")
        print(f"   📝 Registros: {total_records:,}")
        print(f"   💾 Tamaño total: {total_size:.2f}MB")
        print(f"   💽 Promedio por archivo: {total_size/len(log_files):.2f}MB")
        
        return df
        
    except Exception as e:
        print(f"❌ Error analizando logs: {e}")
        return None

def verificar_calidad_logging():
    """Verificar la calidad del sistema de logging"""
    print("\n🔍 VERIFICACIÓN DE CALIDAD DEL LOGGING:")
    print("=" * 45)
    
    log_dir = "logs_obd"
    if not os.path.exists(log_dir):
        print("❌ Sistema de logging no inicializado")
        return
    
    log_files = glob.glob(os.path.join(log_dir, "*.csv"))
    
    issues = []
    recommendations = []
    
    # Verificar tamaño de archivos
    oversized_files = []
    for file in log_files:
        size_mb = os.path.getsize(file) / 1024 / 1024
        if size_mb > 2.5:
            oversized_files.append((file, size_mb))
    
    if oversized_files:
        issues.append(f"🚨 {len(oversized_files)} archivos exceden 2.5MB")
        for file, size in oversized_files:
            print(f"   ⚠️ {os.path.basename(file)}: {size:.2f}MB")
        recommendations.append("Verificar rotación automática de archivos")
    else:
        print("✅ Todos los archivos respetan el límite de 2.5MB")
    
    # Verificar frecuencia de datos
    if log_files:
        latest_file = max(log_files, key=os.path.getmtime)
        try:
            df = pd.read_csv(latest_file)
            if len(df) > 1:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                time_diffs = df['timestamp'].diff().dropna()
                avg_interval = time_diffs.mean().total_seconds()
                
                if avg_interval > 1.0:
                    issues.append(f"⚠️ Frecuencia baja: {1/avg_interval:.2f} Hz")
                    recommendations.append("Verificar configuración de timers")
                elif avg_interval < 0.1:
                    issues.append(f"⚠️ Frecuencia muy alta: {1/avg_interval:.2f} Hz")
                    recommendations.append("Considerar reducir frecuencia para ahorrar espacio")
                else:
                    print(f"✅ Frecuencia adecuada: {1/avg_interval:.2f} Hz")
        except:
            issues.append("❌ Error leyendo archivo más reciente")
    
    # Resumen
    if not issues:
        print("\n🎉 SISTEMA DE LOGGING FUNCIONANDO PERFECTAMENTE")
    else:
        print(f"\n⚠️ ENCONTRADOS {len(issues)} PROBLEMAS:")
        for issue in issues:
            print(f"   {issue}")
        
        if recommendations:
            print(f"\n💡 RECOMENDACIONES:")
            for rec in recommendations:
                print(f"   • {rec}")

if __name__ == "__main__":
    df = analizar_logs_obd()
    verificar_calidad_logging()
    
    print(f"\n💾 Logs disponibles en carpeta: logs_obd/")
    print(f"📊 Usa Excel o cualquier herramienta CSV para análisis adicional")
