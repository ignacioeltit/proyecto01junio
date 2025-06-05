# debug_read_fast_internal.py
def add_parse_response_method():
    """Agrega el método parse_response con debug"""
    
    def parse_response(self, response, pid):
        """Parsea respuesta del ELM327 con debug detallado"""
        print(f'    [DEBUG] Parsing PID {pid}')
        print(f'    [DEBUG] Respuesta cruda: {repr(response)}')
        
        try:
            # Limpiar respuesta
            response = response.replace('\r', '').replace('\n', '').replace('>', '').strip()
            print(f'    [DEBUG] Respuesta limpia: {repr(response)}')
            
            # Buscar respuesta válida (formato: 41 XX YY ZZ)
            import re
            pattern = r'41' + pid[2:4] + r'([0-9A-F]+)'
            print(f'    [DEBUG] Patrón a buscar: {pattern}')
            
            match = re.search(pattern, response.replace(' ', ''))
            
            if not match:
                print(f'    [DEBUG] No match encontrado para {pid}')
                return None
                
            hex_data = match.group(1)
            print(f'    [DEBUG] Hex data extraído: {hex_data}')
            
            # Conversiones según PID
            if pid == '010C':  # RPM
                if len(hex_data) >= 4:
                    rpm = (int(hex_data[:2], 16) * 256 + int(hex_data[2:4], 16)) / 4
                    result = {'name': 'RPM', 'value': int(rpm), 'unit': 'RPM'}
                    print(f'    [DEBUG] RPM calculado: {result}')
                    return result
                    
            elif pid == '010D':  # Velocidad
                if len(hex_data) >= 2:
                    speed = int(hex_data[:2], 16)
                    result = {'name': 'Velocidad', 'value': speed, 'unit': 'km/h'}
                    print(f'    [DEBUG] Velocidad calculada: {result}')
                    return result
                    
            elif pid == '0105':  # Temperatura motor
                if len(hex_data) >= 2:
                    temp = int(hex_data[:2], 16) - 40
                    result = {'name': 'Temp_Motor', 'value': temp, 'unit': 'C'}
                    print(f'    [DEBUG] Temperatura calculada: {result}')
                    return result
                    
            return None
            
        except Exception as e:
            print(f'    [DEBUG] Error parsing {pid}: {e}')
            return None
    
    # Importar y patchear la clase
    from dashboard_optimizado_wifi import OptimizedELM327Connection
    OptimizedELM327Connection.parse_response = parse_response
    
    return OptimizedELM327Connection

if __name__ == "__main__":
    try:
        ELM327Class = add_parse_response_method()
        
        elm = ELM327Class()
        if elm.connect():
            print('CONECTADO OK')
            print(f'Fast PIDs configurados: {elm.fast_pids}')
            
            # Debug manual del método read_fast_data
            print('\n=== DEBUGGING read_fast_data() ===')
            
            # Simular lo que hace read_fast_data internamente
            data = {}
            for pid in elm.fast_pids:
                print(f'\n[MAIN] Procesando PID: {pid}')
                
                # Enviar comando
                command = f'{pid}\r'
                print(f'[MAIN] Enviando: {repr(command)}')
                elm.socket.send(command.encode())
                
                # Esperar respuesta
                import time
                time.sleep(0.5)
                response = elm.socket.recv(512).decode('utf-8', errors='ignore')
                print(f'[MAIN] Respuesta recibida: {repr(response)}')
                
                # Parsear
                parsed = elm.parse_response(response, pid)
                if parsed:
                    data[pid] = parsed
                    print(f'[MAIN] ✅ PID {pid} parseado exitosamente')
                else:
                    print(f'[MAIN] ❌ PID {pid} falló al parsear')
            
            print(f'\n=== RESULTADO FINAL ===')
            print(f'Total PIDs obtenidos: {len(data)}')
            for pid, info in data.items():
                print(f'  {pid}: {info}')
                
            elm.disconnect()
        else:
            print('ERROR: No conectó')
            
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()