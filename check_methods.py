try:
    from dashboard_optimizado_wifi import OptimizedELM327Connection
    
    elm = OptimizedELM327Connection()
    print('Métodos disponibles en la clase:')
    
    methods = [method for method in dir(elm) if not method.startswith('_')]
    for method in methods:
        print(f'  - {method}')
        
    print('\n¿Tiene parse_response?', hasattr(elm, 'parse_response'))
    print('¿Tiene read_fast_data?', hasattr(elm, 'read_fast_data'))
    
except Exception as e:
    print('ERROR:', str(e))