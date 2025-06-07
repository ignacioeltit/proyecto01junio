import sys
import os
sys.path.append('src')
sys.path.append('.')

try:
    from src.obd.emulador import emular_datos_obd2
    from src.obd.pids_ext import PIDS
except ImportError:
    try:
        from obd.emulador import emular_datos_obd2
        from obd.pids_ext import PIDS
    except ImportError:
        print("❌ Error: No se pueden importar los módulos OBD")
        print("   Verificar que estás en el directorio raíz del proyecto")
        exit(1)

def test_emulator_hilux():
    """Prueba el emulador con PIDs específicos del Hilux 2018 Diesel"""
    print("🔧 PROBANDO EMULADOR TOYOTA HILUX 2018 DIESEL")
    print("=" * 60)
    print(f"📊 PIDs disponibles en sistema: {len(PIDS)}")
    print()
    # PIDs críticos para Hilux Diesel
    test_pids = [
        'rpm', 'vel', 'temp', 'carga_motor',
        'boost_pressure', 'turbo_rpm', 'turbo_temp',
        'fuel_rate', 'dpf_temperature', 'egr_commanded',
        'oil_temp', 'control_module_voltage', 'ambient_temp',
        'vin', 'calibration_id'
    ]
    print("🎮 SIMULANDO ESCENARIOS DE CONDUCCIÓN")
    print("-" * 40)
    scenarios = ['ralenti', 'aceleracion', 'crucero', 'frenado']
    for scenario in scenarios:
        print(f"\n🚗 ESCENARIO: {scenario.upper()}")
        print("-" * 30)
        try:
            datos_emulados = emular_datos_obd2(
                escenarios=[{"fase": scenario, "duracion": 1}],
                pids=test_pids
            )
            if datos_emulados and len(datos_emulados) > 0:
                registro = datos_emulados[0]
                for pid in test_pids:
                    if pid in registro:
                        valor = registro[pid]
                        desc = PIDS.get(pid, {}).get('desc', 'Sin descripción')
                        unidad = PIDS.get(pid, {}).get('unidades', '')
                        print(f"  ✅ {pid:20} : {valor:8} {unidad:6} - {desc}")
                    else:
                        print(f"  ❌ {pid:20} : NO_DATA")
            else:
                print(f"  ❌ Error en emulación del escenario {scenario}")
        except Exception as e:
            print(f"  ❌ Error en escenario {scenario}: {str(e)}")
    print(f"\n🔧 VERIFICACIÓN PIDs ESPECÍFICOS DIESEL")
    print("-" * 40)
    diesel_pids = [
        'boost_pressure', 'turbo_rpm', 'fuel_rate', 
        'dpf_temperature', 'egr_commanded'
    ]
    try:
        datos_diesel = emular_datos_obd2(
            escenarios=[{"fase": "aceleracion", "duracion": 1}],
            pids=diesel_pids
        )
        if datos_diesel and len(datos_diesel) > 0:
            registro = datos_diesel[0]
            for pid in diesel_pids:
                if pid in registro and registro[pid] is not None:
                    valor = registro[pid]
                    print(f"  ✅ {pid} funcional: {valor}")
                else:
                    print(f"  ⚠️ {pid} no genera datos")
        else:
            print("  ❌ Error en emulación diesel")
    except Exception as e:
        print(f"  ❌ Error en verificación diesel: {str(e)}")
    print(f"\n📈 RESUMEN DE PRUEBA")
    print("-" * 20)
    try:
        todos_datos = emular_datos_obd2(
            escenarios=[{"fase": "crucero", "duracion": 1}],
            pids=test_pids
        )
        if todos_datos and len(todos_datos) > 0:
            registro = todos_datos[0]
            pids_funcionales = [pid for pid in test_pids if pid in registro and registro[pid] is not None]
            pids_faltantes = [pid for pid in test_pids if pid not in registro or registro[pid] is None]
            print(f"✅ PIDs funcionales: {len(pids_funcionales)}/{len(test_pids)}")
            print(f"❌ PIDs no disponibles: {len(pids_faltantes)}")
            if pids_faltantes:
                print(f"   PIDs faltantes: {', '.join(pids_faltantes)}")
            if len(pids_funcionales) >= len(test_pids) * 0.8:
                print(f"\n🎯 EMULADOR FUNCIONANDO CORRECTAMENTE!")
                print(f"   Listo para pruebas reales con el Hilux")
            else:
                print(f"\n⚠️ Algunos PIDs necesitan revisión")
        else:
            print("❌ Error: No se generaron datos en el resumen")
    except Exception as e:
        print(f"❌ Error en resumen: {str(e)}")

if __name__ == "__main__":
    print("🚗 TOYOTA HILUX 2018 DIESEL - PRUEBA EMULADOR")
    print("=" * 60)
    print("Verificando que todos los PIDs nuevos generen datos correctos...")
    print()
    test_emulator_hilux()
    print("\n" + "=" * 60)
    print("✅ PRUEBA COMPLETADA")
    print("💡 Próximo paso: Prueba real con el vehículo")
