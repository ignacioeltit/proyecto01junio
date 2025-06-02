# Diccionario extendido de PIDs OBD-II estándar SAE J1979
# Fuente: Wikipedia, CSS Electronics, GitHub SAEJ1979
# Última actualización: 2025-06-01

PIDS = {
    '010C': {
        'cmd': '010C',
        'desc': 'Revoluciones por minuto (RPM)',
        'desc_en': 'Engine RPM',
        'bytes': 2,
        'parse': '((A*256)+B)/4',
        'min': 0,
        'max': 16383.75,
        'type': 'int',
    },
    '010D': {
        'cmd': '010D',
        'desc': 'Velocidad del vehículo',
        'desc_en': 'Vehicle speed',
        'bytes': 1,
        'parse': 'A',
        'min': 0,
        'max': 255,
        'type': 'int',
    },
    '0105': {
        'cmd': '0105',
        'desc': 'Temperatura refrigerante',
        'desc_en': 'Engine coolant temperature',
        'bytes': 1,
        'parse': 'A-40',
        'min': -40,
        'max': 215,
        'type': 'int',
    },
    '0110': {
        'cmd': '0110',
        'desc': 'Flujo de aire masivo (MAF)',
        'desc_en': 'MAF air flow rate',
        'bytes': 2,
        'parse': '((A*256)+B)/100',
        'min': 0,
        'max': 655.35,
        'type': 'float',
    },
    '0111': {
        'cmd': '0111',
        'desc': 'Posición del acelerador (TPS)',
        'desc_en': 'Throttle position',
        'bytes': 1,
        'parse': '(A*100)/255',
        'min': 0,
        'max': 100,
        'type': 'float',
    },
    '012F': {
        'cmd': '012F',
        'desc': 'Nivel de combustible',
        'desc_en': 'Fuel level input',
        'bytes': 1,
        'parse': '(A*100)/255',
        'min': 0,
        'max': 100,
        'type': 'float',
    },
    # Puedes agregar más PIDs según lo necesites
}

# Este archivo debe ser usado como referencia principal para selección dinámica,
# validación y parsing de parámetros OBD-II en el sistema.
