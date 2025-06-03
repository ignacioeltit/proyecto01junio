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

---

## Ejecución, logs por sesión y diagnóstico automático

### Ejecución estándar

- Ejecuta SIEMPRE el dashboard desde la raíz del proyecto con:
  ```
  python run_dashboard.py
  ```
- Los imports internos están estandarizados para máxima portabilidad.

### Logging por sesión y análisis automático

- Cada vez que se inicia el dashboard, se crea un archivo de log único por sesión en la raíz, con nombre `log_YYYYMMDD_HHMMSS.txt`.
- El log incluye:
  - Todos los comandos OBD-II enviados y respuestas crudas recibidas.
  - Advertencias si algún PID no responde, no está definido o no se puede parsear.
  - Validación previa de adquisición de PIDs antes de mostrar la UI (en modo real).
  - Resumen automático al cierre: qué PIDs tuvieron datos válidos, cuáles estuvieron vacíos y advertencias relevantes.
- El resumen de sesión se imprime en consola y queda registrado al cerrar la app.

#### Ejemplo de análisis de log de sesión

```
2025-06-02 10:00:00 [INFO] --- INICIO DE SESIÓN OBD-II: log_20250602_100000.txt ---
2025-06-02 10:00:01 [INFO] Enviando comando: 010C (PID: rpm)
2025-06-02 10:00:01 [INFO] Respuesta cruda para 010C (PID: rpm): 410C1130
2025-06-02 10:00:01 [INFO] Enviando comando: 010D (PID: vel)
2025-06-02 10:00:01 [INFO] Respuesta cruda para 010D (PID: vel): 410D28
...
2025-06-02 10:10:00 [INFO] Resumen de sesión:
2025-06-02 10:10:00 [INFO] PIDs con datos válidos: rpm, vel, temp
2025-06-02 10:10:00 [INFO] PIDs siempre vacíos: maf, presion_adm
2025-06-02 10:10:00 [WARNING] Algunos PIDs no recibieron datos válidos durante la sesión.
```

- Puedes auditar cualquier sesión revisando estos archivos de log.
- El CSV exportado siempre incluye todos los PIDs seleccionados y la columna 'escenario'.
