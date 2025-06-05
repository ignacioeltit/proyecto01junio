# fix_parse_response.py
def add_parse_response_method():
    """Agrega el método parse_response faltante a OptimizedELM327Connection"""
    
    def parse_response(self, response, pid):
        """Parsea respuesta del ELM327 y extrae valor del PID"""
        try:
            # Limpiar respuesta
            response = response.replace('\r', '').replace('\n', '').replace('>', '').strip()
            
            # Buscar respuesta válida (formato: 41 XX YY ZZ)
            import re
            pattern = r'41' + pid[2:4] + r'([0-9A-F]+)'
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
            print(f'Error parsing {pid}: {e}')
            return None
    
    # Importar y patchear la clase
    from dashboard_optimizado_wifi import OptimizedELM327Connection
    OptimizedELM327Connection.parse_response = parse_response
    
    print('✅ Método parse_response agregado a OptimizedELM327Connection')
    return OptimizedELM327Connection

if __name__ == "__main__":
    # Test del parche
    try:
        ELM327Class = add_parse_response_method()
        
        elm = ELM327Class()
        if elm.connect():
            print('CONECTADO OK')
            
            # Test con datos reales
            fast_data = elm.read_fast_data()
            print(f'Fast data PIDs: {len(fast_data)}')
            
            if fast_data:
                for pid, data in fast_data.items():
                    print(f'  {pid}: {data}')
            else:
                print('ERROR: Aún no hay datos')
                
            elm.disconnect()
        else:
            print('ERROR: No conectó')
            
    except Exception as e:
        print(f'ERROR: {e}')