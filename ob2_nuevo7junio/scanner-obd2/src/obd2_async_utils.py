import asyncio
from typing import Any, Dict, List, Optional

async def read_vin(elm, logger) -> Optional[str]:
    for attempt in range(3):
        print(f"[DEBUG][read_vin] Intento {attempt+1}: llamando a elm.read_vin_iso_tp()...")
        try:
            vin = await asyncio.wait_for(elm.read_vin_iso_tp(), timeout=5)
        except asyncio.TimeoutError:
            print(f"[DEBUG][read_vin] Timeout en elm.read_vin_iso_tp() (intento {attempt+1})")
            vin = None
        print(f"[DEBUG][read_vin] Resultado intento {attempt+1}: vin={vin}")
        if vin and len(vin) == 17:
            await logger.log_event("info", f"VIN leído correctamente: {vin}")
            return vin
        await logger.log_event("warning", f"Intento {attempt+1} de VIN fallido")
    # Fallback AT
    print("[DEBUG][read_vin] Intentando fallback elm.read_vin_at()...")
    try:
        vin = await asyncio.wait_for(elm.read_vin_at(), timeout=5)
    except asyncio.TimeoutError:
        print("[DEBUG][read_vin] Timeout en elm.read_vin_at() (fallback)")
        vin = None
    print(f"[DEBUG][read_vin] Resultado fallback: vin={vin}")
    if vin and len(vin) == 17:
        await logger.log_event("info", f"VIN leído por AT: {vin}")
        return vin
    await logger.log_event("error", "No se pudo leer el VIN")
    return None

async def read_pids_batch(elm, pids: List[str], logger) -> Dict[str, Any]:
    readings = {}
    for batch in [pids[i:i+9] for i in range(0, len(pids), 9)]:
        batch_result = await elm.read_pids_iso_tp(batch)
        readings.update(batch_result)
        await logger.log_event("info", f"Batch leído: {batch}")
    await logger.log_readings(readings)
    return readings
