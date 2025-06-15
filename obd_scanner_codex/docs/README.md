# OBD-II Automotive Scanner v2 — All Motors

## Objetivo
Esta aplicación proporciona un escáner OBD-II profesional con interfaz gráfica
moderna, capaz de trabajar con un adaptador ELM327 vía WiFi o en modo
simulador. Permite leer múltiples PIDs en tiempo real, administrar códigos DTC y
registrar la sesión de manera asíncrona.

## Estructura del proyecto
```
obd_scanner_codex/
├── main.py
├── core/
│   ├── obd_interface.py
│   ├── pid_manager.py
│   ├── dtc_manager.py
│   ├── vin_reader.py
│   ├── logger.py
│   ├── simulator.py
│   └── config.py
├── ui/
│   ├── gui.py
│   ├── gauges_widget.py
│   ├── realtime_plot.py
│   └── resources/
├── data/
│   └── pid_definitions.json
├── docs/
│   └── README.md
├── requirements.txt
└── .gitignore
```

## Instalación
1. Crear un entorno virtual y activar.
2. Instalar las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Ejecución
```bash
python main.py
```
La aplicación detectará automáticamente si existe conexión con el adaptador
ELM327 en `socket://192.168.0.10:35000`. Si no es posible conectarse,
trabajará en modo simulador.

### Modo real o simulador
1. Edite `config.json` y establezca `"simulator": false` para trabajar con
   el ELM327.
2. Si desea ejecutar siempre en modo simulador, establezca `"simulator": true`.
3. Los cambios de configuración pueden realizarse también desde la pestaña
   *Configuración* de la GUI.

## Ejemplo de uso
Seleccione los PIDs que desee visualizar en la pestaña *PIDs en Vivo* y
presione *Iniciar*. Puede leer y borrar códigos DTC desde la pestaña
*Diagnóstico*.

## Licencia
MIT

_Built to be the ultimate open automotive scanner._
