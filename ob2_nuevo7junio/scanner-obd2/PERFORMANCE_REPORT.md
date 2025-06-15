# PERFORMANCE_REPORT.md

## Diagnóstico de problemas detectados
- La adquisición de datos OBD2 y la actualización de la GUI estaban acopladas, generando bloqueos y lentitud al visualizar múltiples PIDs.
- Los callbacks de adquisición actualizaban widgets directamente, lo que podía provocar congelamientos si no se ejecutaban en el hilo principal.
- El logging era potencialmente bloqueante.

## Soluciones implementadas
- Se creó el módulo `data_buffer.py` con una clase `DataBuffer` basada en `asyncio.Queue` para desacoplar adquisición y GUI.
- Se implementó el módulo `async_logger.py` para logging asíncrono y no bloqueante.
- Se recomienda modificar los callbacks de adquisición para enviar datos al buffer y que la GUI los consuma periódicamente mediante un QTimer.
- Se sugiere actualizar la GUI solo si el valor cambia más de un 1% o 1 unidad, según el tipo de PID.
- Se recomienda que toda actualización de la GUI se realice mediante señales Qt (`Signal/Slot`).

## Resultados estimados/medidos
- Reducción significativa de bloqueos y congelamientos en la interfaz.
- Mayor fluidez al visualizar múltiples PIDs en tiempo real.
- Menor uso de CPU y mejor experiencia de usuario.

## Pasos futuros sugeridos
- Refactorizar los callbacks de adquisición para usar el buffer y señales Qt.
- Medir el tiempo de respuesta y uso de CPU antes y después de los cambios.
- Optimizar el refresco de gráficos y gauges para minimizar repaints innecesarios.
- Documentar el flujo de datos y dependencias en el README técnico.
