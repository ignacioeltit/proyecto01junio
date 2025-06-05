try:
    from dashboard_optimizado_wifi import OptimizedELM327Connection
    
    print('Testing OptimizedELM327Connection...')
    elm = OptimizedELM327Connection()
    
    if elm.connect():
        print('CONECTADO OK')
        
        fast_data = elm.read_fast_data()
        print('Fast data PIDs:', len(fast_data) if fast_data else 0)
        
        if fast_data:
            for pid, data in fast_data.items():
                print('  PID', pid, ':', data)
        else:
            print('ERROR: No se obtuvieron datos')
            
        elm.disconnect()
    else:
        print('ERROR: No se pudo conectar')
        
except Exception as e:
    print('ERROR:', str(e))
