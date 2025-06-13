# elm327_emulator_acquisition

Módulo profesional para la adquisición de datos OBD-II usando un emulador ELM327 (basado en Ircama).

## Características
- Simulación de respuestas ELM327 para comandos OBD-II estándar.
- Adquisición de datos de PIDs en tiempo real o por lotes.
- API clara y extensible para integración con UI o scripts.
- Fácil de extender con nuevos PIDs o comportamientos personalizados.
- Documentación y ejemplos incluidos.

## Estructura
- `simulator.py`: Lógica principal de simulación y respuestas.
- `acquisition.py`: Lógica de adquisición de datos y API de alto nivel.
- `utils.py`: Utilidades para generación de datos, logs, etc.
- `tests/`: Pruebas unitarias y de integración.

## Uso rápido
```python
from elm327_emulator_acquisition.acquisition import EmulatorAcquisition
acq = EmulatorAcquisition()
acq.connect()
data = acq.read_pids(["010C", "010D"])
print(data)
```

## Créditos
Inspirado en [Ircama/ELM327-emulator](https://github.com/Ircama/ELM327-emulator)
