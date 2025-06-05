# fix_read_fast_data_complete.py
def fix_complete_elm327():
    """Reemplaza completamente read_fast_data() con versión funcional"""
    
    def parse_response(self, response, pid):
        """Parsea respuesta del ELM327"""
        try:
            response = response.replace('\r', '').replace('\n', '').replace('>', '').strip()
            
            import re
            pattern = r'41' + pid[2:4] + r'([0-9A-F]{2,4})'
            match = re.search(pattern, response.replace(' ', ''))
            
            if not match:
                return None
                
            hex_data = match.group(1)
            
            if pid == '010C':  # RPM
                if len(hex_data) >= 4:
                    rpm = (int(hex_data[:2], 16) * 256 + int(hex_data[2:4], 16)) / 4
                    return {'name': 'RPM', 'value': int(rpm), 'unit': 'RPM'}
                    
            elif pid == '010D':  # Velocidad
                if len(hex_data) >= 2:
                    speed = int(hex_data[:2], 16)
                    return {'name': 'Velocidad', 'value': speed, 'unit': 'km/h'}
                    
            elif pid == '0105':  # Temperatura motor
                if len(hex_data) >= 2:
                    temp = int(hex_data[:2], 16) - 40
                    return {'name': 'Temp_Motor', 'value': temp, 'unit': 'C'}
                    
            elif pid == '0104':  # Carga motor
                if len(hex_data) >= 2:
                    load = int(hex_data[:2], 16) * 100 / 255
                    return {'name': 'Carga_Motor', 'value': round(load, 1), 'unit': '%'}
                    
            elif pid == '0111':  # Posición acelerador
                if len(hex_data) >= 2:
                    throttle = int(hex_data[:2], 16) * 100 / 255
                    return {'name': 'Acelerador', 'value': round(throttle, 1), 'unit': '%'}
                    
            return None
            
        except Exception as e:
            return None

    def read_fast_data_fixed(self):
        """Versión FUNCIONAL de read_fast_data()"""
        if not self.connected:
            return {}
        
        data = {}
        import time
        
        try:
            for pid in self.fast_pids:
                # Enviar comando
                command = f'{pid}\r'
                self.socket.send(command.encode())
                
                # Esperar respuesta
                time.sleep(0.3)
                response = self.socket.recv(512).decode('utf-8', errors='ignore')
                
                # Parsear usando nuestro método
                parsed = self.parse_response(response, pid)
                if parsed:
                    data[pid] = parsed
                    
        except Exception as e:
            print(f'Error en read_fast_data: {e}')
            
        return data
    
    # Importar y patchear la clase
    from dashboard_optimizado_wifi import OptimizedELM327Connection
    
    # Reemplazar AMBOS métodos
    OptimizedELM327Connection.parse_response = parse_response
    OptimizedELM327Connection.read_fast_data = read_fast_data_fixed
    
    print('✅ Métodos parse_response y read_fast_data REEMPLAZADOS')
    return OptimizedELM327Connection

if __name__ == "__main__":
    try:
        ELM327Class = fix_complete_elm327()
        
        elm = ELM327Class()
        if elm.connect():
            print('🚗 CONECTADO OK')
            
            # Test con método reemplazado
            fast_data = elm.read_fast_data()
            print(f'📊 PIDs obtenidos: {len(fast_data)}')
            
            if fast_data:
                for pid, data in fast_data.items():
                    print(f'  {data["name"]}: {data["value"]} {data["unit"]}')
            else:
                print('❌ Aún no hay datos')
                
            elm.disconnect()
            
            if len(fast_data) >= 3:
                print('\n🎉 ¡PERFECTO! Dashboard debería funcionar ahora')
                print('👉 Ejecuta: python dashboard_optimizado_wifi.py')
                print('👉 Selecciona modo "ELM327 WiFi"')
            else:
                print('\n⚠️  Necesitamos más debugging')
                
        else:
            print('❌ No conectó')
            
    except Exception as e:
        print(f'❌ ERROR: {e}')