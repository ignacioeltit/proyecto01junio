try:
    from dashboard_optimizado_wifi import OptimizedELM327Connection
    
    print('Debugging read_fast_data...')
    elm = OptimizedELM327Connection()
    
    if elm.connect():
        print('CONECTADO OK')
        
        # Test manual de PIDs que sabemos que funcionan
        test_pids = ['010C', '010D', '0105']  # RPM, Velocidad, Temperatura
        
        for pid in test_pids:
            print(f'\nProbando PID {pid}:')
            
            # Enviar comando manualmente
            elm.socket.send(f'{pid}\r'.encode())
            import time
            time.sleep(0.5)
            response = elm.socket.recv(512).decode('utf-8', errors='ignore')
            print(f'  Respuesta cruda: {repr(response)}')
            
            # Probar el método parse_response 
            try:
                parsed = elm.parse_response(response, pid)
                print(f'  Parseado: {parsed}')
            except Exception as e:
                print(f'  Error parsing: {e}')
        
        elm.disconnect()
    else:
        print('ERROR: No se pudo conectar')
        
except Exception as e:
    print('ERROR:', str(e))