# Vitácora de Desarrollo

## 2025-06-07
- Creación de la estructura base y módulos principales.
- Documentación inicial y setup de logging.

## 2025-06-08 a 2025-06-10
- Refactorización completa para usar python-OBD en toda la comunicación OBD-II (conexión, escaneo de PIDs, datos en vivo, DTCs).
- Implementación robusta de conexión ELM327 WiFi y manejo de errores.
- Rediseño de la GUI: solo widgets necesarios, campos para VIN y protocolo, y feedback de usuario mejorado.
- Funciones `leer_vin()` y `scan_protocol()` implementadas con decodificación VIN usando vininfo (fabricante, año, país) y detección de protocolo OBD-II.
- Selector de PID y lista multipid con nombres legibles, actualización en tiempo real del valor seleccionado.
- Pestaña multi-PID con checkboxes y streaming asíncrono usando python-OBD Async, con limpieza y logging adecuado.
- Detención automática del stream asíncrono al cambiar de pestaña o cerrar la ventana.
- Pestaña "Diagnóstico" para lectura/borrado de DTCs con feedback al usuario.
- Integración de AnalogGaugeWidget para visualización analógica en tiempo real de cada PID seleccionado.
- Instalación y verificación de dependencias: vininfo, QT-PyQt-PySide-Custom-Widgets, PySide6.
- Resolución de problemas de dependencias Cairo en macOS.
- Corrección de acceso a comandos OBD usando `obd.commands['PID']`.
- Búsqueda y validación de VIN en logs mediante regex y revisión manual.
- Revisión y recopilación de toda la documentación y bitácora del proyecto.
- Estado: Aplicación estable, funcional y documentada. Listo para pruebas avanzadas y despliegue.

## 2025-06-11
- Integración completa del flujo de obtención de VIN, validación y fallback manual en la UI.
- Si el VIN OBD-II es inválido o no se obtiene, se habilita la selección manual de Marca, Modelo y Año (combos reactivos).
- Los combos se alimentan dinámicamente desde la base de datos de vehículos instalada.
- Se verifica la reactividad: al cambiar la Marca, el combo de Modelo se actualiza automáticamente.
- Pruebas exitosas en simulador y hardware real.
- Documentado el flujo y las instrucciones de verificación en el README.
- Estado: integración automática y fallback robusto funcionando correctamente.
