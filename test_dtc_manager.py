import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'diagnostico'))
import dtc_manager

def print_estado_mil():
    print("\n--- Estado MIL y cantidad de DTCs activos ---")
    estado = dtc_manager.leer_estado_mil()
    if estado.get("error"):
        print(f"Error: {estado['error']}")
        return False
    mil = estado.get("mil")
    num_dtcs = estado.get("num_dtcs")
    print(f"Luz MIL encendida: {'Sí' if mil else 'No'}")
    print(f"Cantidad de DTCs activos: {num_dtcs}")
    return True

def print_dtcs():
    print("\n--- Códigos DTC activos ---")
    dtcs = dtc_manager.leer_dtc()
    if not dtcs or (dtcs[0].get("codigo") is None and dtcs[0].get("descripcion")):
        print(dtcs[0]["descripcion"])
        return []
    for d in dtcs:
        print(f"Código: {d['codigo']}")
        print(f"  Descripción: {d['descripcion']}")
        print(f"  Sugerencia: {d['sugerencia']}")
        print(f"  PIDs recomendados: {', '.join(d['pids_relevantes']) if 'pids_relevantes' in d else 'N/A'}\n")
    return [pid for d in dtcs for pid in d.get('pids_relevantes', [])]

def preguntar_si(msg):
    resp = input(f"{msg} (s/n): ").strip().lower()
    return resp == 's' or resp == 'si' or resp == 'y'

def capturar_pids(pids):
    if not pids:
        print("No hay PIDs sugeridos para capturar.")
        return
    print(f"\nCapturando los siguientes PIDs durante 30 segundos: {', '.join(set(pids))}")
    muestras = dtc_manager.captura_pids(list(set(pids)), 30)
    if muestras and isinstance(muestras, list) and "error" in muestras[0]:
        print(f"Error: {muestras[0]['error']}")
        return
    print(f"Se capturaron {len(muestras)} muestras:")
    for i, muestra in enumerate(muestras, 1):
        print(f"{i:02d}: {muestra}")
        time.sleep(0.05)

def borrar_dtcs():
    print("\nBorrando DTCs...")
    res = dtc_manager.borrar_dtc()
    if res.get("exito"):
        print("DTCs borrados correctamente.")
    else:
        print(f"Error: {res.get('mensaje', 'No se pudo borrar DTCs')}")

def main():
    print("==== Prueba de dtc_manager.py ====")
    if not print_estado_mil():
        return
    pids = print_dtcs()
    if pids and preguntar_si("¿Desea capturar los PIDs sugeridos durante 30 segundos?"):
        capturar_pids(pids)
    if preguntar_si("¿Desea borrar los DTCs?"):
        borrar_dtcs()
    print("\nPrueba finalizada.")

if __name__ == "__main__":
    main()
