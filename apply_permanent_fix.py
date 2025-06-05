# apply_permanent_fix.py
import shutil
import re

def backup_and_fix_dashboard():
    """Hace backup y aplica el arreglo permanente al dashboard"""
    
    print('🔄 Creando backup del archivo original...')
    shutil.copy('dashboard_optimizado_wifi.py', 'dashboard_optimizado_wifi_backup.py')
    print('✅ Backup creado: dashboard_optimizado_wifi_backup.py')
    
    # Leer archivo original
    with open('dashboard_optimizado_wifi.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Nuevo método parse_response para agregar
    parse_response_method = '''
    def parse_response(self, response, pid):
        """Parsea respuesta del ELM327 correctamente"""
        try:
            # Limpiar respuesta
            response = response.replace('\\r', '').replace('\\n', '').replace('>', '').strip()
            
            # Buscar respuesta válida (formato: 41 XX YY)
            import re
            pattern = r'41' + pid[2:4] + r'([0-9A-F]{2,4})'
            match = re.search(pattern, response.replace(' ', ''))
            
            if not match:
                return None
                
            hex_data = match.group(1)
            
            # Conversiones según PID
            if pid == '010C':  # RPM
                if len(hex_data) >= 4:
                    rpm = (int(hex_data[:2], 16) * 256 + int(hex_data[2:4], 16)) / 4
                    return {'name': 'RPM', 'value': int(rpm), 'unit': 'RPM'}
                    
            elif pid == '010D':  # Velocidad
                if len(hex_data) >= 2:
                    speed = int(hex_data[:2], 16)
                    return {'name': 'Velocidad', 'value': speed, 'unit': 'km/h'}
                    
            elif pid == '0105':  # Temperatura motor
                if len(hex_data) >= 2:
                    temp = int(hex_data[:2], 16) - 40
                    return {'name': 'Temp_Motor', 'value': temp, 'unit': 'C'}
                    
            elif pid == '0104':  # Carga motor
                if len(hex_data) >= 2:
                    load = int(hex_data[:2], 16) * 100 / 255
                    return {'name': 'Carga_Motor', 'value': round(load, 1), 'unit': '%'}
                    
            elif pid == '0111':  # Posición acelerador
                if len(hex_data) >= 2:
                    throttle = int(hex_data[:2], 16) * 100 / 255
                    return {'name': 'Acelerador', 'value': round(throttle, 1), 'unit': '%'}
                    
            return None
            
        except Exception as e:
            return None
'''

    # Nuevo método read_fast_data corregido
    new_read_fast_data = '''    def read_fast_data(self):
        """Lectura rápida de PIDs principales - VERSIÓN CORREGIDA"""
        if not self.connected:
            return {}
        
        data = {}
        import time
        
        try:
            for pid in self.fast_pids:
                # Enviar comando PID
                command = f'{pid}\\r'
                self.socket.send(command.encode())
                
                # Esperar respuesta
                time.sleep(0.3)
                response = self.socket.recv(512).decode('utf-8', errors='ignore')
                
                # Parsear respuesta usando método corregido
                parsed = self.parse_response(response, pid)
                if parsed:
                    data[pid] = parsed
                    
        except Exception as e:
            print(f'Error en read_fast_data: {e}')
            
        return data'''
    
    # Dividir contenido en líneas
    lines = content.split('\\n')
    
    # Encontrar líneas de los métodos
    read_fast_data_start = -1
    read_fast_data_end = -1
    
    for i, line in enumerate(lines):
        if 'def read_fast_data(' in line:
            read_fast_data_start = i
            # Encontrar el final del método (siguiente def o final de clase)
            for j in range(i + 1, len(lines)):
                if (lines[j].strip().startswith('def ') and 
                    not lines[j].strip().startswith('def ') or 
                    lines[j].startswith('class ') or
                    (j == len(lines) - 1)):
                    read_fast_data_end = j
                    break
            break
    
    if read_fast_data_start == -1:
        print('❌ No se encontró el método read_fast_data')
        return False
    
    # Reemplazar el método read_fast_data
    new_lines = (lines[:read_fast_data_start] + 
                new_read_fast_data.split('\\n') + 
                lines[read_fast_data_end:])
    
    # Agregar método parse_response antes del método read_slow_data
    read_slow_data_line = -1
    for i, line in enumerate(new_lines):
        if 'def read_slow_data(' in line:
            read_slow_data_line = i
            break
    
    if read_slow_data_line != -1:
        # Insertar parse_response antes de read_slow_data
        new_lines = (new_lines[:read_slow_data_line] + 
                    parse_response_method.split('\\n') + 
                    new_lines[read_slow_data_line:])
    
    # Escribir archivo modificado
    new_content = '\\n'.join(new_lines)
    
    with open('dashboard_optimizado_wifi.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print('✅ Archivo dashboard_optimizado_wifi.py modificado exitosamente')
    print('✅ Método parse_response agregado')
    print('✅ Método read_fast_data reemplazado')
    
    return True

if __name__ == "__main__":
    try:
        if backup_and_fix_dashboard():
            print('\\n🎉 ¡ARREGLO PERMANENTE COMPLETADO!')
            print('\\n👉 Ahora puedes ejecutar:')
            print('   python dashboard_optimizado_wifi.py')
            print('\\n📁 Si algo sale mal, restaura con:')
            print('   copy dashboard_optimizado_wifi_backup.py dashboard_optimizado_wifi.py')
        else:
            print('❌ Error aplicando el arreglo')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()