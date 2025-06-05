# fix_indentation_correct.py
def fix_dashboard_correctly():
    """Arregla el dashboard con indentación correcta"""
    
    print('📄 Leyendo archivo original...')
    with open('dashboard_optimizado_wifi.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Encontrar dónde insertar parse_response (antes de read_slow_data)
    insert_line = -1
    read_fast_data_start = -1
    read_fast_data_end = -1
    
    for i, line in enumerate(lines):
        if 'def read_fast_data(' in line:
            read_fast_data_start = i
        elif 'def read_slow_data(' in line:
            insert_line = i
            if read_fast_data_start != -1:
                read_fast_data_end = i
            break
    
    if insert_line == -1 or read_fast_data_start == -1:
        print('❌ No se encontraron los métodos necesarios')
        return False
    
    # Método parse_response con indentación correcta
    parse_response_lines = [
        '\n',
        '    def parse_response(self, response, pid):\n',
        '        """Parsea respuesta del ELM327 correctamente"""\n',
        '        try:\n',
        '            # Limpiar respuesta\n',
        '            response = response.replace(\'\\r\', \'\').replace(\'\\n\', \'\').replace(\'>\', \'\').strip()\n',
        '            \n',
        '            # Buscar respuesta válida (formato: 41 XX YY)\n',
        '            import re\n',
        '            pattern = r\'41\' + pid[2:4] + r\'([0-9A-F]{2,4})\'\n',
        '            match = re.search(pattern, response.replace(\' \', \'\'))\n',
        '            \n',
        '            if not match:\n',
        '                return None\n',
        '                \n',
        '            hex_data = match.group(1)\n',
        '            \n',
        '            # Conversiones según PID\n',
        '            if pid == \'010C\':  # RPM\n',
        '                if len(hex_data) >= 4:\n',
        '                    rpm = (int(hex_data[:2], 16) * 256 + int(hex_data[2:4], 16)) / 4\n',
        '                    return {\'name\': \'RPM\', \'value\': int(rpm), \'unit\': \'RPM\'}\n',
        '                    \n',
        '            elif pid == \'010D\':  # Velocidad\n',
        '                if len(hex_data) >= 2:\n',
        '                    speed = int(hex_data[:2], 16)\n',
        '                    return {\'name\': \'Velocidad\', \'value\': speed, \'unit\': \'km/h\'}\n',
        '                    \n',
        '            elif pid == \'0105\':  # Temperatura motor\n',
        '                if len(hex_data) >= 2:\n',
        '                    temp = int(hex_data[:2], 16) - 40\n',
        '                    return {\'name\': \'Temp_Motor\', \'value\': temp, \'unit\': \'C\'}\n',
        '                    \n',
        '            elif pid == \'0104\':  # Carga motor\n',
        '                if len(hex_data) >= 2:\n',
        '                    load = int(hex_data[:2], 16) * 100 / 255\n',
        '                    return {\'name\': \'Carga_Motor\', \'value\': round(load, 1), \'unit\': \'%\'}\n',
        '                    \n',
        '            elif pid == \'0111\':  # Posición acelerador\n',
        '                if len(hex_data) >= 2:\n',
        '                    throttle = int(hex_data[:2], 16) * 100 / 255\n',
        '                    return {\'name\': \'Acelerador\', \'value\': round(throttle, 1), \'unit\': \'%\'}\n',
        '                    \n',
        '            return None\n',
        '            \n',
        '        except Exception as e:\n',
        '            return None\n',
        '\n'
    ]
    
    # Método read_fast_data corregido
    new_read_fast_data_lines = [
        '    def read_fast_data(self):\n',
        '        """Lectura rápida de PIDs principales - VERSIÓN CORREGIDA"""\n',
        '        if not self.connected:\n',
        '            return {}\n',
        '        \n',
        '        data = {}\n',
        '        import time\n',
        '        \n',
        '        try:\n',
        '            for pid in self.fast_pids:\n',
        '                # Enviar comando PID\n',
        '                command = f\'{pid}\\r\'\n',
        '                self.socket.send(command.encode())\n',
        '                \n',
        '                # Esperar respuesta\n',
        '                time.sleep(0.3)\n',
        '                response = self.socket.recv(512).decode(\'utf-8\', errors=\'ignore\')\n',
        '                \n',
        '                # Parsear respuesta usando método corregido\n',
        '                parsed = self.parse_response(response, pid)\n',
        '                if parsed:\n',
        '                    data[pid] = parsed\n',
        '                    \n',
        '        except Exception as e:\n',
        '            print(f\'Error en read_fast_data: {e}\')\n',
        '            \n',
        '        return data\n',
        '\n'
    ]
    
    # Construir nuevo archivo
    new_lines = (lines[:read_fast_data_start] + 
                new_read_fast_data_lines + 
                parse_response_lines + 
                lines[read_fast_data_end:])
    
    # Escribir archivo corregido
    with open('dashboard_optimizado_wifi.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print('✅ Archivo corregido con indentación correcta')
    return True

if __name__ == "__main__":
    try:
        if fix_dashboard_correctly():
            print('\n🎉 ¡ARREGLO APLICADO CORRECTAMENTE!')
            print('\n👉 Ejecuta: python dashboard_optimizado_wifi.py')
        else:
            print('❌ Error en el arreglo')
    except Exception as e:
        print(f'❌ Error: {e}')