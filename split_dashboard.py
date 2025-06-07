import re
import os

def split_python_file(input_file, output_dir='modules'):
    """
    Divide un archivo Python grande en módulos más pequeños basados en clases y funciones.
    
    Args:
        input_file (str): Ruta al archivo Python a dividir
        output_dir (str): Directorio donde se guardarán los módulos
    """
    # Crear directorio si no existe
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Leer el archivo completo
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extraer imports
    imports = []
    import_pattern = r'^(?:from|import).*$'
    for line in content.split('\n'):
        if re.match(import_pattern, line):
            imports.append(line)
    
    # Patrón para detectar clases
    class_pattern = r'class\s+(\w+).*?(?=(?:class|\Z))'
    classes = re.finditer(class_pattern, content, re.DOTALL | re.MULTILINE)
    
    # Guardar cada clase en un archivo separado
    for class_match in classes:
        class_name = class_match.group(1)
        class_content = class_match.group(0)
        
        # Crear archivo para la clase
        filename = f"{output_dir}/{class_name.lower()}.py"
        with open(filename, 'w', encoding='utf-8') as f:
            # Escribir imports
            f.write('"""\nMódulo para la clase ' + class_name + '\n"""\n\n')
            for imp in imports:
                f.write(imp + '\n')
            f.write('\n\n')
            
            # Escribir contenido de la clase
            f.write(class_content)
    
    # Crear __init__.py
    with open(f"{output_dir}/__init__.py", 'w', encoding='utf-8') as f:
        f.write('"""\nPaquete de módulos del dashboard OBD-II\n"""\n\n')
        # Importar todas las clases
        for file in os.listdir(output_dir):
            if file.endswith('.py') and file != '__init__.py':
                module_name = file[:-3]
                class_name = module_name.capitalize()
                f.write(f'from .{module_name} import {class_name}\n')

if __name__ == '__main__':
    input_file = 'dashboard_optimizado_wifi_final.py'
    split_python_file(input_file)
    print("✅ Archivo dividido en módulos exitosamente")
