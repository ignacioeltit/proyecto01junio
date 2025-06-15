"""
vin_decoder.py - Decodificador de VIN offline según ISO 3779/3780
"""
import os
import json
import re
import sqlite3

class VinDecoder:
    def __init__(self):
        base = os.path.join(os.path.dirname(__file__), 'vin_data')
        with open(os.path.join(base, 'wmi_codes.json'), encoding='utf-8') as f:
            self.wmi_codes = json.load(f)
        with open(os.path.join(base, 'year_codes.json'), encoding='utf-8') as f:
            self.year_codes = json.load(f)

    def validar_vin(self, vin):
        vin = vin.upper()
        if len(vin) != 17:
            return False, "El VIN debe tener 17 caracteres."
        if any(c in vin for c in 'IOQ'):
            return False, "El VIN no debe contener I, O ni Q."
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
            return False, "El VIN contiene caracteres inválidos."
        return True, "VIN válido."

    def calcular_digito_control(self, vin):
        translit = {c: i for c, i in zip('ABCDEFGHJKLMNPRSTUVWXYZ',
            [1,2,3,4,5,6,7,8,1,2,3,4,5,7,8,9,2,3,4,5,6,7,8,9])}
        translit.update({str(i): i for i in range(10)})
        pesos = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2]
        suma = 0
        for i, c in enumerate(vin):
            v = translit.get(c, 0)
            suma += v * pesos[i]
        resto = suma % 11
        return 'X' if resto == 10 else str(resto)

    def decode(self, vin):
        vin = vin.strip().upper()
        valido, msg = self.validar_vin(vin)
        if not valido:
            return {'vin': vin, 'valido': False, 'error': msg}
        wmi = vin[:3]
        vds = vin[3:9]
        vis = vin[9:]
        pais = self.wmi_codes.get(wmi, {}).get('country', 'Desconocido')
        fabricante = self.wmi_codes.get(wmi, {}).get('manufacturer', 'Desconocido')
        # Año: buscar primero por código simple, luego por código extendido (A2, B2, ...)
        anio = self.year_codes.get(vin[9], None)
        if anio is None:
            anio = self.year_codes.get(vin[9] + '2', 'Desconocido')
        planta = vin[10]
        secuencia = vin[11:]
        digito = self.calcular_digito_control(vin)
        return {
            'vin': vin,
            'valido': True,
            'pais': pais,
            'fabricante': fabricante,
            'anio': anio,
            'planta': planta,
            'secuencia': secuencia,
            'digito_control': digito,
            'digito_control_ok': digito == vin[8]
        }

    def buscar_en_base_local(self, vin: str):
        db_path = os.path.join("data", "vpic_lite.db")
        if not os.path.exists(db_path):
            print("❌ Base local vPIC no encontrada.")
            return None

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # permite acceso por nombre de columna
            cursor = conn.cursor()

            # buscar por coincidencia parcial de VIN
            cursor.execute("""
                SELECT 
                    v.MakeId, v.ModelId, v.EngineId, v.FuelTypeId, v.BodyClassId, 
                    v.PlantCity, v.ModelYear
                FROM Vehicle v
                WHERE v.VIN LIKE ? LIMIT 1
            """, (vin[:11] + "%",))
            row = cursor.fetchone()

            if not row:
                print("⚠️ VIN no encontrado en base local.")
                return None

            # buscar datos extendidos desde otras tablas
            make = cursor.execute("SELECT MakeName FROM Make WHERE MakeId = ?", (row["MakeId"],)).fetchone()
            model = cursor.execute("SELECT ModelName FROM Model WHERE ModelId = ?", (row["ModelId"],)).fetchone()
            engine = cursor.execute("SELECT EngineConfiguration FROM Engine WHERE EngineId = ?", (row["EngineId"],)).fetchone()
            fuel = cursor.execute("SELECT FuelTypeName FROM FuelType WHERE FuelTypeId = ?", (row["FuelTypeId"],)).fetchone()
            body = cursor.execute("SELECT BodyClassName FROM BodyClass WHERE BodyClassId = ?", (row["BodyClassId"],)).fetchone()

            conn.close()

            return {
                "marca": make["MakeName"] if make else None,
                "modelo": model["ModelName"] if model else None,
                "año": row["ModelYear"],
                "tipo_motor": engine["EngineConfiguration"] if engine else None,
                "tipo_combustible": fuel["FuelTypeName"] if fuel else None,
                "clase_carroceria": body["BodyClassName"] if body else None,
                "planta": row["PlantCity"]
            }

        except Exception as e:
            print(f"❌ Error consultando base local: {e}")
            return None
