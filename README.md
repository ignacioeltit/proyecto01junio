# Sistema de Captura y Logging de Datos OBD-II

Proyecto Python para captura, visualización y exportación de datos OBD-II usando ELM327 (USB/WiFi).

## Diccionario extendido de PIDs

El archivo `src/obd/pids_ext.py` contiene el diccionario extendido de PIDs OBD-II estándar SAE J1979, con nombre, descripción, comando, bytes, fórmula, rango y tipo de dato. Es la referencia principal para selección dinámica y validación de parámetros en el sistema.

## Columna 'escenario' en logs OBD-II

- El sistema registra en cada línea del log el escenario, modo o fase activa de simulación/adquisición (columna 'escenario').
- Esta columna es obligatoria en todos los logs exportados, y refleja el modo seleccionado en la UI o el backend.
- Permite auditar, analizar y correlacionar los valores de los PIDs con el contexto de conducción (ej: 'ralenti', 'aceleracion', 'crucero', 'frenado', etc.).
- El flujo completo (emulador, UI, backend y exportador) fuerza la presencia y actualización de esta columna.
- Validar siempre que la columna 'escenario' esté presente y sea coherente con los datos y la selección de la UI.

### Ejemplo de registro exportado:

| timestamp           | rpm  | vel | escenario   |
|---------------------|------|-----|-------------|
| 2025-06-02 10:00:00 | 850  | 0   | ralenti     |
| 2025-06-02 10:00:01 | 2200 | 90  | crucero     |
| 2025-06-02 10:00:02 | 800  | 0   | frenado     |

---

## Emulador OBD-II: lógica de generación de PIDs y extensión

El emulador (`src/obd/emulador.py`) genera datos realistas para cada PID soportado según el escenario de conducción. Si se solicita un PID no soportado, se exporta vacío y se emite una advertencia en consola y log.

### PIDs soportados y lógica por escenario

- **rpm**: Ralenti 800-950, aceleración sube hasta 4500, crucero 1800-2500, frenado baja.
- **vel**: 0 en ralenti, sube en aceleración, estable 90-120 en crucero, baja en frenado.
- **temp**: Sube hasta 85-95°C, baja si se excede.
- **maf**: Proporcional a rpm, con ruido.
- **throttle**: 10 en ralenti, sube en aceleración, 20 en crucero, baja en frenado.
- **consumo**: Bajo en ralenti/frenado, alto en aceleración, medio en crucero.
- **presion_adm**: Baja en ralenti/frenado, alta en aceleración, media en crucero.
- **volt_bateria**: 13.5-14.0V, leve ruido.
- **carga_motor**: Baja en ralenti/frenado, alta en aceleración, media en crucero.
- **escenario**: Nombre de la fase activa (ralenti, aceleracion, crucero, frenado, etc).

### Añadir nuevos PIDs al emulador

1. Agrega una función `gen_<pid>(fase, estado)` en `emulador.py` con docstring breve y lógica.
2. Añade la función al diccionario `pid_generators`.
3. El valor generado debe actualizar y devolver `estado[pid]`.
4. El sistema los incluirá automáticamente si se seleccionan en la UI.

### Protocolo para PIDs no soportados

- Si se solicita un PID no soportado, la columna aparece vacía en el log/exportación.
- Se imprime y loguea una advertencia: "Advertencia: El PID solicitado '<PID>' no está soportado en la emulación. Se exportará vacío."
- Así, el usuario puede distinguir entre "sin datos" por falta de soporte y un bug real.

### Validación visual y en log

- Todos los PIDs seleccionados aparecen como columnas en la UI y el log.
- Los valores son realistas si el PID está soportado.
- Si no está soportado, la columna está vacía y se muestra advertencia en consola/log.
