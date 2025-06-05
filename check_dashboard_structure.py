# check_dashboard_structure.py
try:
    with open('dashboard_optimizado_wifi.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar la clase OptimizedELM327Connection
    lines = content.split('\n')
    
    class_start = -1
    read_fast_data_line = -1
    class_end = -1
    
    for i, line in enumerate(lines):
        if 'class OptimizedELM327Connection' in line:
            class_start = i
            print(f'Clase encontrada en línea {i+1}')
        
        if 'def read_fast_data(' in line:
            read_fast_data_line = i
            print(f'Método read_fast_data encontrado en línea {i+1}')
        
        if class_start != -1 and line.startswith('class ') and 'OptimizedELM327Connection' not in line:
            class_end = i
            break
    
    if class_end == -1:
        class_end = len(lines)
    
    print(f'\nEstructura de la clase:')
    print(f'  - Inicio: línea {class_start+1}')
    print(f'  - read_fast_data: línea {read_fast_data_line+1}')
    print(f'  - Fin estimado: línea {class_end}')
    
    # Mostrar métodos actuales de la clase
    print(f'\nMétodos encontrados en la clase:')
    in_class = False
    for i, line in enumerate(lines):
        if i == class_start:
            in_class = True
        elif i == class_end:
            in_class = False
        
        if in_class and line.strip().startswith('def '):
            method_name = line.strip().split('(')[0].replace('def ', '')
            print(f'  - {method_name} (línea {i+1})')
    
except Exception as e:
    print(f'Error: {e}')