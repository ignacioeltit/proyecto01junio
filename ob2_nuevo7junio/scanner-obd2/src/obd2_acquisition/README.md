# obd2_acquisition

Módulo profesional para la adquisición de datos OBD-II reales desde la ECU del vehículo.

## Características
- Conexión robusta a dispositivos ELM327 físicos (USB, Bluetooth, WiFi).
- Lectura de PIDs estándar y personalizados.
- API asíncrona y extensible para integración con UI y backend.
- Manejo de errores, reconexión y logging avanzado.
- Ejemplo de uso y pruebas unitarias.

## Ejemplo rápido
```python
from obd2_acquisition.core import OBD2Acquisition
acq = OBD2Acquisition(port="/dev/ttyUSB0")
await acq.connect()
pids = await acq.get_supported_pids()
data = await acq.read_pids(["010C", "010D"])
print(data)
```

## Estructura
- `core.py`: Lógica principal de adquisición y API.
- `utils.py`: Utilidades y helpers.
- `tests/`: Pruebas unitarias.

## Licencia
MIT
