# 🧪 Script de prueba para inspeccionar la decodificación VIN con vininfo

from vininfo import Vin

# Reemplaza con el VIN que estás leyendo (puede venir de self.le_vin o de un test)
vin_test = "5FNYF5H59HB011946"  # ejemplo real de Honda

try:
    v = Vin(vin_test)
    print("✅ VIN válido y parseable:", vin_test)
    print("  País:", v.country)
    print("  Fabricante:", v.manufacturer)
    try:
        print("  Región:", v.region)
    except AttributeError:
        print("ℹ️  Región: atributo no disponible")
    print("  WMI:", v.wmi)
    print("  VDS:", v.vds)
    print("  VIS:", v.vis)
    print("  Checksum válido:", v.verify_checksum())
    print("\n🔍 Detalle completo (annotate):")
    for line in v.annotate():
        print(" ", line)
except Exception as e:
    print("❌ Error al decodificar VIN:", vin_test)
    print("   Detalle del error:", e)
