# Arquitectura del Proyecto Scanner OBD2

El proyecto está organizado en módulos independientes para facilitar la escalabilidad y el mantenimiento. Cada componente tiene responsabilidades claras y comunicación bien definida.

## Módulos principales
- `core/`: Lógica de comunicación, parsing y gestión de PIDs/DTCs.
- `ui/`: Interfaz de usuario CLI y visualización de datos.
- `utils/`: Utilidades, simulador ECU y constantes.
