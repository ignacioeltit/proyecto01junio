# Documentación Técnica: protocol_detector.py

## Descripción General
`protocol_detector.py` es un módulo Python independiente para la autodetección de protocolos OBD-II usando adaptadores ELM327 (WiFi, USB o Serial). Permite a cualquier aplicación o dashboard identificar automáticamente el protocolo de comunicación del vehículo y verificar la conectividad básica, facilitando la compatibilidad universal con vehículos OBD-II.

## Características
- **Autodetección de protocolo:** Utiliza comandos AT estándar (`ATZ`, `ATSP 0`, `ATDP`) para identificar el protocolo activo.
- **Prueba de comunicación:** Envía un PID estándar (`0100`) para verificar que la comunicación es válida.
- **Soporte para protocolos comunes:** Incluye CAN, ISO9141, KWP2000, J1850PWM, J1850VPW y modo automático.
- **Interfaz simple:** Clase `ProtocolDetector` con método `detect()` para integración sencilla.
- **Validación de respuesta:** Verifica que la respuesta OBD-II sea válida antes de confirmar el protocolo.

## Uso
### Ejemplo básico
```python
from src.obd.protocol_detector import ProtocolDetector
# Suponiendo que 'connection' es un objeto con send_command() y read_response()
detector = ProtocolDetector(connection)
protocolo, exito, respuesta = detector.detect()
print(f"Protocolo detectado: {protocolo}, éxito: {exito}, respuesta: {respuesta}")
```

### Métodos principales
- `__init__(self, connection)`: Recibe un objeto de conexión ELM327 (debe implementar `send_command(cmd:str)` y `read_response(timeout:float)`).
- `detect(self)`: Realiza la autodetección y devuelve `(nombre_protocolo, exito:bool, respuesta:str)`.

## Detalles de Implementación
- **PROTOCOL_LIST:** Lista de protocolos a probar si la autodetección falla.
- **TEST_PID:** PID estándar (`0100`) usado para verificar comunicación.
- **_is_valid_response:** Método estático para validar si la respuesta recibida es OBD-II estándar.

## Integración
- Puede usarse en cualquier dashboard o backend que requiera identificar el protocolo OBD-II antes de iniciar la comunicación.
- Permite cargar perfiles de vehículo o ajustar la lógica de parsing según el protocolo detectado.

## Requisitos
- Python 3.7+
- Un objeto de conexión ELM327 que implemente los métodos mencionados.

## Ejemplo de objeto de conexión mínimo
```python
class DummyConnection:
    def send_command(self, cmd):
        print(f"Enviando: {cmd}")
    def read_response(self, timeout=2):
        return "41 00 98 3B 80 13"  # Respuesta simulada válida
    def clear_buffer(self):
        pass
```

## Autoría y Licencia
- Autor: Equipo Inteligencia Automotriz
- Fecha: 2025-06-05
- Licencia: MIT (puede adaptarse según el proyecto)

---

Este archivo debe mantenerse junto al módulo y actualizarse si se agregan nuevos protocolos o funcionalidades.
