# MODULE_OVERVIEW_APP_PRINCIPAL.md

## Resumen funcional

La app principal es un escáner OBD2 profesional desarrollado en Python (PySide6), orientado a diagnóstico automotriz, adquisición y visualización de datos en tiempo real desde vehículos mediante ELM327 (WiFi/Bluetooth/USB). Permite leer el VIN, DTCs, visualizar y graficar parámetros (PIDs) en gauges personalizados, cuenta con logging robusto por sesión, modo demo visual sin hardware, y un sistema de fallback manual para identificación de vehículo.

### Flujo de datos principal
1. **Inicialización**: Configuración de entorno, logging y carga de recursos.
2. **Conexión**: Detección y conexión a ELM327, identificación de protocolo OBD-II.
3. **Lectura de VIN**: Obtención automática; si falla, entrada manual y fallback reactivo (Marca/Modelo/Año).
4. **Selección de PIDs**: El usuario elige los parámetros a visualizar (multipid, gauges).
5. **Adquisición y visualización**: Streaming asíncrono de datos, actualización de UI (gauges, tablas, logs).
6. **Logging**: Registro estructurado de eventos, errores y datos por sesión.
7. **Modo demo**: Visualización animada de gauges sin conexión OBD2.

## Dependencias Python
- PySide6
- pyserial
- matplotlib
- vininfo (opcional, para decodificación avanzada de VIN)

## Recursos utilizados
- **Estáticos/UI**: `src/ui/canvas_gauge.html`, `src/ui/gauge.min.js`, `src/ui/qwebchannel.js`
- **Widgets**: `src/ui/widgets/simple_gauge.py`
- **Bases de datos**: `data/vehicle_makes_models.json`, `data/pid_definitions.json`, `data/dtc_definitions.json`
- **Logs**: `logs/app_YYYYMMDD_HHMMSS.log`, `logs/obd_log_*.csv`

## Estructura de carpetas relevante
- `src/main.py`: Entrada principal
- `src/ui/data_visualizer.py`: UI principal y lógica de visualización
- `src/ui/widgets/simple_gauge.py`: Widget de gauge visual custom
- `src/obd2_acquisition/core.py`: Backend de adquisición OBD-II asíncrono
- `src/ui/pid_acquisition.py`: Pestaña de adquisición de PIDs
- `demo_gauges.py`: Script de demo visual
- `tests/`: Pruebas unitarias

## Puntos de integración para módulos nuevos
- **Tuning/Performance**: Añadir pestañas o widgets en `data_visualizer.py` y nuevos módulos en `src/ui/`.
- **Nuevos PIDs**: Agregar definiciones en `data/pid_definitions.json` y lógica en backend.
- **Exportación/Reportes**: Integrar en la UI y usar los logs estructurados.
- **Simuladores**: Extender el modo demo o crear nuevos scripts en `src/ui/`.

## Entorno y configuración VS Code sugerido
- **Extensiones recomendadas**:
  - ms-python.python
  - ms-python.vscode-pylance
  - ms-toolsai.jupyter (opcional)
- **settings.json**:
  - Formateador: black o autopep8
  - Python > Linting: enabled
- **launch.json**:
  - Configuración para lanzar `src/main.py` y `demo_gauges.py`
- **.env**:
  - Variables de entorno para puertos OBD2, si aplica

## Mapa visual de dependencias/componentes

```
main.py
│
├── ui/data_visualizer.py
│     ├── widgets/simple_gauge.py
│     └── pid_acquisition.py
│
├── obd2_acquisition/core.py
│
├── data/*.json (vehículos, PIDs, DTCs)
│
├── logs/
└── demo_gauges.py
```

## Sugerencias de mejora
- **Tests**: Ampliar cobertura en `tests/` para UI, adquisición y fallback VIN.
- **Validaciones**: Validar entradas manuales y datos OBD2 en frontend y backend.
- **CI/CD**: Integrar workflows de GitHub Actions para lint, test y build multiplataforma.
- **Documentación**: Mantener actualizado este overview y los diagramas en `/docs/`.
- **Internacionalización**: Soporte multilenguaje en la UI.
- **Accesibilidad**: Mejorar contraste y navegación por teclado en la UI.

---

> Última actualización: 12/06/2025
