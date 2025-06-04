# Manual Interno para la Integración de Nuevos PIDs OBD-II

> **Basado en el caso exitoso de integración del PID 0105 (Temperatura de Refrigerante)**

---

## Índice
1. [Selección del PID](#selección-del-pid)
2. [Documentación del PID](#documentación-del-pid)
3. [Ampliación del diccionario/lista de PIDs soportados](#ampliación-del-diccionariolista-de-pids-soportados)
4. [Modificación del parser o función de lectura](#modificación-del-parser-o-función-de-lectura)
5. [Validación y testeo](#validación-y-testeo)
6. [Integración visual (dashboard)](#integración-visual-dashboard)
7. [Buenas prácticas y troubleshooting](#buenas-prácticas-y-troubleshooting)
8. [Checklist final de integración](#checklist-final-de-integración)
9. [Recomendaciones para automatización](#recomendaciones-para-automatización)

---

## 1. Selección del PID
- Consulta la documentación oficial SAE J1979, la wiki de OBD-II o fuentes confiables.
- Elige un PID estándar o propietario que aporte valor al monitoreo.
- Ejemplo: PID `0105` (Temperatura de refrigerante).

## 2. Documentación del PID
Registra los siguientes datos mínimos:
- **Código PID:** Ejemplo: `0105`
- **Nombre legible:** Ejemplo: `temp`
- **Descripción:** Ejemplo: `Temperatura refrigerante`
- **Unidades:** Ejemplo: `°C`
- **Bytes:** Ejemplo: `1`
- **Fórmula de conversión:** Ejemplo: `A-40`
- **Ejemplo de respuesta:** Ejemplo: `41057B -> 0x7B-40 = 83°C`
- **Fuente:** Documentación SAE, manual del fabricante, etc.

## 3. Ampliación del diccionario/lista de PIDs soportados
- Abre el archivo centralizado: `src/obd/pids_ext.py`.
- Agrega una nueva entrada en el diccionario `PIDS` siguiendo el formato:

```python
PIDS = {
    # ...existing code...
    "0105": {
        "cmd": "0105",
        "nombre": "temp",
        "desc": "Temperatura refrigerante",
        "desc_en": "Engine coolant temperature",
        "unidades": "°C",
        "bytes": 1,
        "parse": "A-40",
        "min": -40,
        "max": 215,
        "type": "int",
        "ejemplo": "41057B -> 0x7B-40 = 83°C",
        # El parse_fn se asigna abajo para usar la función robusta
    },
    # ...existing code...
}
```
- Añade el mapeo en `PID_MAP`:
```python
PID_MAP = {
    # ...existing code...
    "0105": "temp",
    # ...existing code...
}
```

## 4. Modificación del parser o función de lectura
- Si el PID requiere un parser especial, define una función robusta:

```python
def parse_temp_refrigerante(resp):
    """
    Parsea la respuesta cruda del PID 0105 (temperatura refrigerante).
    Acepta formatos: '41 05 7B', '41057B', etc.
    Devuelve temperatura en °C o None si no es válida.
    """
    if not resp or not isinstance(resp, str):
        return None
    raw = resp.replace("\r", "").replace("\n", "").strip()
    raw_sin_espacios = raw.replace(" ", "")
    if raw_sin_espacios.startswith("4105") and len(raw_sin_espacios) >= 6:
        try:
            temp = int(raw_sin_espacios[4:6], 16) - 40
            return temp
        except ValueError:
            return None
    partes = raw.split()
    if len(partes) >= 3 and partes[0] == "41" and partes[1] == "05":
        try:
            temp = int(partes[2], 16) - 40
            return temp
        except ValueError:
            return None
    return None

# Asociar la función al PID:
PIDS["0105"]["parse_fn"] = parse_temp_refrigerante
```

- Si el parser genérico es suficiente, omite este paso.

## 5. Validación y testeo
- Reinicia la app y selecciona el nuevo PID en el dashboard.
- Verifica que el valor se muestre correctamente y que no haya errores en consola/log.
- Si hay errores, revisa el parser y la definición del PID.

## 6. Integración visual (dashboard)
- El dashboard toma automáticamente los PIDs definidos en `PIDS`.
- Si el PID tiene nombre y descripción, aparecerá en la lista de selección y en los gauges.
- No es necesario modificar la UI salvo casos especiales.

## 7. Buenas prácticas y troubleshooting
- Mantén el archivo `pids_ext.py` como única fuente de verdad.
- Documenta cada PID con comentarios si es poco común.
- Usa nombres legibles y consistentes.
- Si un PID no funciona, revisa:
  - El código hexadecimal y la fórmula de conversión.
  - El parser asociado.
  - El log de errores.

## 8. Checklist final de integración
- [ ] El PID está documentado y agregado en `PIDS` y `PID_MAP`.
- [ ] Si requiere, tiene parser robusto y está asociado.
- [ ] Se visualiza correctamente en el dashboard.
- [ ] No hay errores en consola/log.
- [ ] El valor es coherente con la respuesta OBD-II.

## 9. Recomendaciones para automatización
- Considera crear un script que genere automáticamente la plantilla de un nuevo PID a partir de un formulario o CSV.
- Automatiza tests unitarios para parsers de PIDs.
- Usa validadores automáticos para detectar duplicados o inconsistencias en el diccionario de PIDs.

---

**¡Listo! Siguiendo este manual, la integración de nuevos PIDs será rápida, limpia y libre de errores.**
