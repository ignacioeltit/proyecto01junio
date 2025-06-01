# Lectura y definición de PIDs OBD-II

# Definición de PIDs OBD-II para el MVP

PIDS = {
    'rpm': {
        'cmd': '010C',
        'desc': 'Revoluciones por minuto (RPM)',
        'parse': lambda data: (
            ((data[0] * 256) + data[1]) // 4
        ) if len(data) >= 2 else None
    },
    'speed': {
        'cmd': '010D',
        'desc': 'Velocidad del vehículo (km/h)',
        'parse': lambda data: data[0] if len(data) >= 1 else None
    }
}
