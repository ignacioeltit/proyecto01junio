# Scanner OBD2 Profesional

## Objetivo
Desarrollar un escáner automotriz OBD2 profesional en Python 3.11+ compatible con ELM327 (WiFi/Bluetooth/USB), capaz de leer VIN, DTCs, datos en vivo y graficar parámetros.

## Estructura del Proyecto
- Modular, escalable y documentado.
- Soporte para logs, simulador ECU, selección dinámica de PIDs y visualización de datos.

## Uso Básico
1. Instala dependencias: `pip install -r requirements.txt`
2. Ejecuta: `python src/main.py`

# OBD2 Async Scanner Premium

## Ejecución

```bash
python src/main_async.py
```

## Logs
- Se generan en `/logs/SESSION.json` en formato estructurado.
- Ejemplo:
```json
{
  "session": "20250609_184617",
  "vin": "1HGCM82633A123456",
  "readings": { "010C": 2200, "010D": 84 },
  "events": [ { "time": "...", "type": "info", "message": "PID timeout" } ]
}
```

## Personalización
- Modifica la lista de PIDs en el código o UI.
- Ajusta el tamaño de lote en la función `read_pids_batch`.

## Tests
- Ejecuta `pytest` en la carpeta `tests/` para pruebas unitarias.

## Características premium
- Backend 100% asíncrono (`asyncio`), sin threads.
- Logger JSON no bloqueante por sesión.
- Lectura robusta de VIN (multi-frame, fallback, validación).
- Batching de PIDs y cache por VIN.
- Heartbeat y reconexión automática.
- Hooks para UI: indicadores de PIDs caídos, botón de rescan, campo VIN y estado de conexión.

## Flujo de obtención de VIN y fallback manual

Al iniciar la aplicación, el sistema intenta leer el VIN automáticamente desde la ECU vía OBD-II:
- Si el VIN es válido, se decodifica usando `vininfo` y se muestran fabricante, año y país.
- Si el VIN es inválido, incompleto o no se puede leer, se habilita la entrada manual y el usuario puede ingresar el VIN.
- Si el VIN manual sigue siendo inválido o el usuario lo omite, se activa el modo fallback: aparecen los combos de selección de Marca, Modelo y Año.

### Fallback y UI reactiva
- Los combos de Marca, Modelo y Año se habilitan solo si el VIN no es válido.
- Al cambiar la Marca, la lista de Modelos se actualiza automáticamente según la selección.
- El Año puede ser seleccionado libremente o filtrado según la base de datos de vehículos.
- El sistema utiliza la base de datos de vehículos instalada (vehicle-makes/open-vehicle-db) para poblar los combos.

### Verificación del flujo
1. Ejecuta la app y conecta a un vehículo real o simulador OBD-II.
2. Si el VIN se obtiene correctamente, verifica que se muestre la información decodificada.
3. Si el VIN no se obtiene o es inválido, prueba ingresar uno manualmente.
4. Si el VIN manual es inválido o se omite, verifica que los combos de Marca/Modelo/Año se activen y sean reactivos.
5. Cambia la Marca y observa que el combo de Modelo se actualiza dinámicamente.

Este flujo asegura compatibilidad universal y una experiencia de usuario robusta incluso en vehículos sin soporte completo de VIN OBD-II.

## Licencia
MIT License
