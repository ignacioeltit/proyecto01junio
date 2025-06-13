# TUNING_OVERVIEW.md

## Descripción general

El módulo de Tuning permite seleccionar y visualizar en tiempo real PIDs críticos para ajuste fino (AFR, EGT, knock, trims, boost, timing, etc.) según el vehículo activo. Integra gauges y gráficos en vivo, y emite la señal:

```
tuning_update(session_id, map_version, pid_values_dict)
```

## Widget principal
- Archivo: `src/ui/tuning_widget.py`
- Selector múltiple de PIDs (según vehículo, desde `data/pid_definitions.json`).
- Visualización en vivo: gauges y gráfico.
- Señal: `tuning_update(session_id, map_version, pid_values_dict)`

## Integración UI
- Pestaña "Tuning" en `data_visualizer.py`.
- Recarga dinámica de PIDs al cambiar de vehículo.

## Backend
- Suscribe automáticamente los PIDs seleccionados.
- Envía eventos de datos traducidos a la UI y logger.

## Logging profesional
- Logger con RotatingFileHandler.
- Formato JSON por línea (JSON Lines):

```json
{
  "timestamp": "2025-06-12T12:00:00Z",
  "level": "INFO",
  "module": "tuning",
  "session_id": "abc",
  "map_version": "v1",
  "VIN": "123",
  "make": "Ford",
  "model": "Focus",
  "rpm": 2000,
  "speed": 80,
  "afr": 14.7,
  "egt": 800,
  "boost": 1.2,
  "trims": 0.98,
  "timing": 12,
  "flags": {"WOT": true, "fallback": false, "knock_detected": false}
}
```

## Ejemplo de uso
1. Selecciona PIDs críticos en la pestaña Tuning.
2. Observa valores en gauges y gráfico en tiempo real.
3. La señal `tuning_update` se emite automáticamente con los datos actuales.

## Pruebas
- Ejecuta:
  ```bash
  pytest
  ```
- Verifica que los tests de `tests/test_tuning.py` pasen correctamente.

## Integración y pasos
- Añade el widget a la UI.
- Conecta la señal al backend y logger.
- Asegura recarga dinámica de PIDs según vehículo.
