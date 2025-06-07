# INSTRUCCIÓN MAESTRA PARA INTEGRACIÓN DE NUEVOS PIDs OBD-II

## Objetivo
Asegurar que la integración de nuevos PIDs OBD-II en el sistema sea controlada, trazable y centralizada, evitando duplicidades y garantizando la robustez en UI, backend, emulador, exportador y tests.

---

## Metodología Paso a Paso

1. **Definir el nuevo PID en `src/obd/pids_ext.py`**
   - Agregar entrada con clave legible (ej: `temp_agua`) y campos: `cmd`, `desc`, `min`, `max`, `parse_fn` (si aplica).
   - Ejemplo para PID 0105 (temperatura de refrigerante):
     ```python
     PIDS["temp_agua"] = {
         "cmd": "0105",
         "desc": "Temperatura refrigerante",
         "min": -40,
         "max": 215,
         "parse_fn": parse_temp_agua,  # Definir función de parsing si es necesario
     }
     ```

2. **Implementar función de parsing si es necesario**
   - Ejemplo:
     ```python
     def parse_temp_agua(resp):
         # resp: '41 05 XX' o '4105XX'
         if not resp:
             return None
         raw = resp.replace(" ", "")
         if raw.startswith("4105") and len(raw) >= 6:
             try:
                 temp = int(raw[4:6], 16) - 40
                 return temp
             except Exception:
                 return None
         return None
     ```

3. **Actualizar UI y lógica de selección**
   - No es necesario modificar la UI si usas el flujo estándar: los PIDs definidos en `pids_ext.py` aparecen automáticamente.
   - Verifica que el nombre legible y la descripción sean claros.

4. **Actualizar emulador**
   - Si el PID requiere lógica de emulación específica, modifícala en el método correspondiente del emulador (`OBDDataSource`).

5. **Agregar/actualizar tests**
   - Añadir test unitario para el parsing y para la adquisición en modo emulador y real.
   - Ejemplo de test:
     ```python
     def test_parse_temp_agua():
         assert parse_temp_agua("41 05 7B") == 83
         assert parse_temp_agua("41057B") == 83
         assert parse_temp_agua("") is None
     ```

6. **Validar integración**
   - Ejecutar la app, seleccionar el nuevo PID, verificar que:
     - Aparece en la UI y log/exportación.
     - No hay duplicados.
     - El valor cambia correctamente (emulador y real).
   - Ejecutar el test automatizado de PIDs.

7. **Actualizar documentación y bitácora**
   - Registrar la integración en README y bitácora.
   - Anotar fecha, autor, PID, y pruebas realizadas.

8. **Generar informe de PIDs operativos** (opcional pero recomendado)
   - Ejecutar el script de auditoría o exportar el listado de PIDs activos y su parsing.

9. **Validación obligatoria antes de commit/backup**
   - Confirmar manualmente que la integración cumple todos los puntos anteriores.
   - No realizar commit ni backup sin validación explícita.

---

## Ejemplo de registro en bitácora

- 2025-06-03 | Integrado PID 0105 (temp_agua) siguiendo metodología maestra. Test unitario y validación manual OK. No se detectan duplicados. Documentación y log actualizados.

---

## Notas
- Toda integración debe ser trazable y auditable.
- Si tienes dudas, consulta README y los informes de auditoría.
- Para dudas sobre parsing, revisa ejemplos en `pids_ext.py` y tests.
