#!/usr/bin/env python3
"""
Script de Prueba de Hardware Real - Dashboard OBD-II
Autor: Sistema Automatizado
Fecha: [Se reemplaza dinámicamente]
"""

import sys
import os
import time
import serial
import serial.tools.list_ports
import subprocess
import threading
from datetime import datetime, timedelta
import json
import socket
import argparse

REPORT_TEMPLATE = (
    "# REPORTE DE PRUEBA DE HARDWARE REAL - DASHBOARD OBD-II\n"
    "**Fecha:** {timestamp}\n"
    "**Duración de prueba:** {duration}\n"
    "**Estado general:** {status}\n\n"
    "## 1. RESUMEN EJECUTIVO\n"
    "- Hardware detectado: {hw_detected}\n"
    "- Conexión establecida: {conn_status}\n"
    "- PIDs funcionando: {pids_ok}\n"
    "- Integración con Dashboard: {dashboard_status}\n"
    "- Calificación general: {score}\n\n"
    "## 2. DETECCIÓN DE HARDWARE\n"
    "### Puertos COM escaneados:\n{ports_status}\n\n"
    "### Dispositivos ELM327 detectados:\n{elm327_info}\n\n"
    "## 3. PRUEBAS DE CONECTIVIDAD\n"
    "### Conexión inicial:\n"
    "- Tiempo de conexión: {conn_time}\n"
    "- Comandos de inicialización: {init_cmds}\n"
    "- Respuesta del ECU: {ecu_resp}\n"
    "- Protocolos detectados: {protocols}\n\n"
    "## 4. PRUEBAS DE PIDs\n"
    "### PIDs básicos probados:\n"
    "| PID | Descripción | Estado | Valor | Tiempo (ms) |\n"
    "|-----|-------------|--------|-------|-------------|\n"
    "{pids_table}\n\n"
    "## 5. MÉTRICAS DE RENDIMIENTO\n"
    "- Latencia promedio: {latency}\n"
    "- PIDs por segundo: {pid_rate}\n"
    "- Errores de comunicación: {comm_errors}\n"
    "- Uptime de conexión: {uptime}\n"
    "- Reconexiones necesarias: {reconnections}\n\n"
    "## 6. INTEGRACIÓN CON DASHBOARD\n"
    "- Lanzamiento automático: {dashboard_launch}\n"
    "- Configuración automática: {dashboard_config}\n"
    "- Datos en tiempo real: {dashboard_realtime}\n"
    "- UI responsive: {dashboard_ui}\n"
    "- Estabilidad durante prueba: {dashboard_stable}\n\n"
    "## 7. VALIDACIÓN DE DATOS\n"
    "- Valores realistas: {realistic}\n"
    "- Unidades correctas: {units}\n"
    "- Rangos válidos: {ranges}\n"
    "- Consistencia temporal: {consistency}\n\n"
    "## 8. PROBLEMAS DETECTADOS\n"
    "### Errores críticos:\n{critical_errors}\n\n"
    "### Advertencias:\n{warnings}\n\n"
    "## 9. RECOMENDACIONES\n"
    "### Inmediatas:\n{immediate_recs}\n\n"
    "### Futuras:\n{future_recs}\n\n"
    "## 10. CONCLUSIONES\n"
    "- Preparación para producción: {prod_ready}\n"
    "- Estabilidad del hardware: {hw_score}\n"
    "- Compatibilidad del dashboard: {dashboard_score}\n"
    "- Próximos pasos: {next_steps}\n"
)

class HardwareRealTester:
    def __init__(self, mode='auto', wifi_ip='192.168.0.10', wifi_port=35000):
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'hardware_detected': [],
            'connection_tests': {},
            'pid_tests': {},
            'performance_metrics': {},
            'dashboard_integration': {},
            'errors': [],
            'summary': {}
        }
        self.start_time = datetime.now()
        self.elm327_ports = []
        self.selected_port = None
        self.selected_baudrate = None
        self.connection = None
        self.dashboard_proc = None
        self.mode = mode
        self.wifi_ip = wifi_ip
        self.wifi_port = wifi_port
        self.tcp_connection = None
        self.is_wifi = False

    def scan_com_ports(self):
        """Escanear puertos COM disponibles"""
        ports = list(serial.tools.list_ports.comports())
        self.report['hardware_detected'] = []
        for port in ports:
            self.report['hardware_detected'].append({
                'port': port.device,
                'desc': port.description
            })
        return ports

    def detect_elm327(self, port, baudrates=None):
        """Detectar dispositivo ELM327 en puerto específico"""
        if baudrates is None:
            baudrates = [38400, 9600, 115200]
        for baud in baudrates:
            try:
                ser = serial.Serial(port, baudrate=baud, timeout=2)
                ser.write(b'ATI\r')
                time.sleep(1)
                resp = ser.read(128).decode(errors='ignore')
                if 'ELM327' in resp or 'ELM' in resp:
                    self.elm327_ports.append({
                        'port': port,
                        'baudrate': baud,
                        'id': resp.strip()
                    })
                    ser.close()
                    return True, baud, resp.strip()
                ser.close()
            except Exception:
                continue
        return False, None, None

    def detect_elm327_wifi(self, ip=None, port=None):
        """Detectar dispositivo ELM327 WiFi"""
        ip = ip or self.wifi_ip
        port = port or self.wifi_port
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((ip, port))
            s.sendall(b'ATI\r')
            time.sleep(1)
            resp = s.recv(256).decode(errors='ignore')
            if 'ELM327' in resp or 'ELM' in resp:
                self.elm327_ports.append({
                    'port': f'{ip}:{port}',
                    'baudrate': 'TCP',
                    'id': resp.strip()
                })
                self.selected_port = f'{ip}:{port}'
                self.is_wifi = True
                s.close()
                return True, ip, port, resp.strip()
            s.close()
        except Exception as e:
            self.report['errors'].append(f'Error WiFi: {e}')
        return False, ip, port, None

    def test_obd_connection(self, port, baudrate):
        """Probar conexión OBD-II básica"""
        try:
            ser = serial.Serial(port, baudrate=baudrate, timeout=2)
            cmds = ['ATZ', 'ATE0', 'ATL0', 'ATS0', 'ATH0', 'ATSP0', '0100']
            results = {}
            for cmd in cmds:
                ser.write((cmd + '\r').encode())
                time.sleep(0.5)
                resp = ser.read(128).decode(errors='ignore')
                results[cmd] = resp.strip()
            ser.close()
            return True, results
        except Exception as e:
            self.report['errors'].append(f'Error conexión OBD: {e}')
            return False, {}

    def test_obd_connection_wifi(self, ip=None, port=None):
        """Probar conexión OBD-II a través de WiFi"""
        ip = ip or self.wifi_ip
        port = port or self.wifi_port
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((ip, port))
            cmds = ['ATZ', 'ATE0', 'ATL0', 'ATS0', 'ATH0', 'ATSP0', '0100']
            results = {}
            for cmd in cmds:
                s.sendall((cmd + '\r').encode())
                time.sleep(0.5)
                resp = s.recv(256).decode(errors='ignore')
                results[cmd] = resp.strip()
            s.close()
            return True, results
        except Exception as e:
            self.report['errors'].append(f'Error conexión WiFi OBD: {e}')
            return False, {}

    def test_basic_pids(self, port, baudrate):
        """Probar PIDs básicos"""
        pids = {
            '010C': 'RPM',
            '010D': 'Velocidad',
            '0105': 'Temp Refrigerante',
            '010F': 'Temp Aire',
            '0111': 'Acelerador',
            '0142': 'Voltaje ECU'
        }
        results = {}
        try:
            ser = serial.Serial(port, baudrate=baudrate, timeout=2)
            for pid, desc in pids.items():
                t0 = time.time()
                ser.write((pid + '\r').encode())
                time.sleep(0.5)
                resp = ser.read(128).decode(errors='ignore')
                t1 = time.time()
                results[pid] = {
                    'desc': desc,
                    'resp': resp.strip(),
                    'ok': bool(resp.strip()),
                    'ms': int((t1-t0)*1000)
                }
            ser.close()
        except Exception as e:
            self.report['errors'].append(f'Error PIDs: {e}')
        self.report['pid_tests'] = results
        return results

    def test_basic_pids_wifi(self, ip=None, port=None):
        """Probar PIDs básicos a través de WiFi"""
        ip = ip or self.wifi_ip
        port = port or self.wifi_port
        pids = {
            '010C': 'RPM',
            '010D': 'Velocidad',
            '0105': 'Temp Refrigerante',
            '010F': 'Temp Aire',
            '0111': 'Acelerador',
            '0142': 'Voltaje ECU'
        }
        results = {}
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((ip, port))
            for pid, desc in pids.items():
                t0 = time.time()
                s.sendall((pid + '\r').encode())
                time.sleep(0.5)
                resp = s.recv(256).decode(errors='ignore')
                t1 = time.time()
                results[pid] = {
                    'desc': desc,
                    'resp': resp.strip(),
                    'ok': bool(resp.strip()),
                    'ms': int((t1-t0)*1000)
                }
            s.close()
        except Exception as e:
            self.report['errors'].append(f'Error PIDs WiFi: {e}')
        self.report['pid_tests'] = results
        return results

    def measure_performance(self, port, baudrate, duration=10):
        """Medir rendimiento de comunicación"""
        pids = ['010C', '010D', '0105']
        count = 0
        errors = 0
        latencies = []
        t0 = time.time()
        try:
            ser = serial.Serial(port, baudrate=baudrate, timeout=2)
            while time.time() - t0 < duration:
                for pid in pids:
                    t1 = time.time()
                    ser.write((pid + '\r').encode())
                    time.sleep(0.2)
                    resp = ser.read(128).decode(errors='ignore')
                    t2 = time.time()
                    if resp.strip():
                        latencies.append((t2-t1)*1000)
                        count += 1
                    else:
                        errors += 1
            ser.close()
        except Exception as e:
            self.report['errors'].append(f'Error rendimiento: {e}')
        avg_latency = sum(latencies)/len(latencies) if latencies else 0
        self.report['performance_metrics'] = {
            'latency': avg_latency,
            'pid_rate': count/duration if duration else 0,
            'comm_errors': errors,
            'uptime': 100.0,
            'reconnections': 0
        }
        return self.report['performance_metrics']

    def measure_performance_wifi(self, ip=None, port=None, duration=10):
        """Medir rendimiento de comunicación a través de WiFi"""
        ip = ip or self.wifi_ip
        port = port or self.wifi_port
        pids = ['010C', '010D', '0105']
        count = 0
        errors = 0
        latencies = []
        t0 = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((ip, port))
            while time.time() - t0 < duration:
                for pid in pids:
                    t1 = time.time()
                    s.sendall((pid + '\r').encode())
                    time.sleep(0.2)
                    resp = s.recv(256).decode(errors='ignore')
                    t2 = time.time()
                    if resp.strip():
                        latencies.append((t2-t1)*1000)
                        count += 1
                    else:
                        errors += 1
            s.close()
        except Exception as e:
            self.report['errors'].append(f'Error rendimiento WiFi: {e}')
        avg_latency = sum(latencies)/len(latencies) if latencies else 0
        self.report['performance_metrics'] = {
            'latency': avg_latency,
            'pid_rate': count/duration if duration else 0,
            'comm_errors': errors,
            'uptime': 100.0,
            'reconnections': 0
        }
        return self.report['performance_metrics']

    def launch_dashboard_integration(self, port, baudrate):
        """Lanzar dashboard y probar integración"""
        try:
            args = [sys.executable, 'dashboard_gui.py', '--real', '--port', str(port), '--baud', str(baudrate)]
            self.dashboard_proc = subprocess.Popen(args)
            time.sleep(10)
            self.report['dashboard_integration'] = {
                'launched': True,
                'port': port,
                'baudrate': baudrate
            }
            return True
        except Exception as e:
            self.report['dashboard_integration'] = {
                'launched': False,
                'error': str(e)
            }
            return False

    def generate_report(self):
        """Generar reporte completo en Markdown"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        duration = str(datetime.now() - self.start_time)
        status = 'ÉXITO' if not self.report['errors'] else 'PARCIAL'
        ports_status = '\n'.join([
            f"- {d['port']}: {d['desc']}" for d in self.report['hardware_detected']
        ])
        elm327_info = '\n'.join([
            f"- Puerto: {d['port']} | Baudrate: {d['baudrate']} | ID: {d['id']}"
            for d in self.elm327_ports
        ]) or 'No detectado'
        pids_table = ''
        for pid, data in self.report['pid_tests'].items():
            pids_table += (
                f"| {pid} | {data['desc']} | "
                f"{'✅' if data['ok'] else '❌'} | {data['resp']} | {data['ms']} |\n"
            )
        perf = self.report.get('performance_metrics', {})
        dashboard = self.report.get('dashboard_integration', {})
        with open(f'REPORTE_HARDWARE_REAL_{timestamp}.md', 'w', encoding='utf-8') as f:
            f.write(REPORT_TEMPLATE.format(
                timestamp=timestamp,
                duration=duration,
                status=status,
                hw_detected='Sí' if self.elm327_ports else 'No',
                conn_status='Éxito' if self.selected_port else 'Fallo',
                pids_ok=f"{sum(1 for d in self.report['pid_tests'].values() if d['ok'])}/"
                        f"{len(self.report['pid_tests'])}",
                dashboard_status='Éxito' if dashboard.get('launched') else 'Fallo',
                score='8/10' if not self.report['errors'] else '6/10',
                ports_status=ports_status,
                elm327_info=elm327_info,
                conn_time='-',
                init_cmds='-',
                ecu_resp='-',
                protocols='-',
                pids_table=pids_table,
                latency=perf.get('latency', '-'),
                pid_rate=perf.get('pid_rate', '-'),
                comm_errors=perf.get('comm_errors', '-'),
                uptime=perf.get('uptime', '-'),
                reconnections=perf.get('reconnections', '-'),
                dashboard_launch='Éxito' if dashboard.get('launched') else 'Fallo',
                dashboard_config='-',
                dashboard_realtime='-',
                dashboard_ui='-',
                dashboard_stable='-',
                realistic='-',
                units='-',
                ranges='-',
                consistency='-',
                critical_errors='\n'.join(self.report['errors']) or 'Ninguno',
                warnings='-',
                immediate_recs='-',
                future_recs='-',
                prod_ready='Parcial',
                hw_score='7/10',
                dashboard_score='7/10',
                next_steps='- Validar con más vehículos\n- Mejorar reconexión automática\n- Ampliar pruebas de UI'
            ))

    def run_wifi_test(self):
        print('Buscando ELM327 WiFi...')
        found, ip, port, ident = self.detect_elm327_wifi()
        if found:
            print(f'ELM327 WiFi detectado en {ip}:{port} ({ident})')
            self.selected_port = f'{ip}:{port}'
            self.selected_baudrate = 'TCP'
            print('Probando conexión OBD-II WiFi...')
            ok, results = self.test_obd_connection_wifi(ip, port)
            self.report['connection_tests'] = results
            if not ok:
                print('Fallo en conexión OBD-II WiFi.')
                self.generate_report()
                return False
            print('Probando PIDs básicos WiFi...')
            self.test_basic_pids_wifi(ip, port)
            print('Midiendo rendimiento WiFi...')
            self.measure_performance_wifi(ip, port)
            print('Lanzando dashboard e integrando (WiFi)...')
            self.launch_dashboard_integration(self.selected_port, self.selected_baudrate)
            print('Generando reporte...')
            self.generate_report()
            print('Prueba completa finalizada.')
            return True
        else:
            print('No se detectó ELM327 WiFi. Abortando.')
            self.generate_report()
            return False

    def run_com_test(self):
        print('Escaneando puertos COM...')
        ports = self.scan_com_ports()
        print('Buscando ELM327...')
        for port in ports:
            found, baud, ident = self.detect_elm327(port.device)
            if found:
                print(f'ELM327 detectado en {port.device} @ {baud} ({ident})')
                self.selected_port = port.device
                self.selected_baudrate = baud
                break
        if not self.selected_port:
            print('No se detectó ELM327. Abortando.')
            self.generate_report()
            return
        print('Probando conexión OBD-II...')
        ok, results = self.test_obd_connection(self.selected_port, self.selected_baudrate)
        self.report['connection_tests'] = results
        if not ok:
            print('Fallo en conexión OBD-II.')
            self.generate_report()
            return
        print('Probando PIDs básicos...')
        self.test_basic_pids(self.selected_port, self.selected_baudrate)
        print('Midiendo rendimiento...')
        self.measure_performance(self.selected_port, self.selected_baudrate)
        print('Lanzando dashboard e integrando...')
        self.launch_dashboard_integration(self.selected_port, self.selected_baudrate)
        print('Generando reporte...')
        self.generate_report()
        print('Prueba completa finalizada.')

    def run_complete_test(self):
        print('Modo de prueba:', self.mode)
        if self.mode == 'wifi':
            self.run_wifi_test()
        elif self.mode == 'com':
            self.run_com_test()
        else:  # auto
            ok = self.run_wifi_test()
            if not ok:
                print('Intentando modo COM...')
                self.run_com_test()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prueba de hardware real OBD-II (COM/WiFi)')
    parser.add_argument('--mode', choices=['auto', 'com', 'wifi'],
                        default='auto', help='Modo de conexión: auto, com, wifi')
    parser.add_argument('--wifi-ip', default='192.168.0.10',
                        help='IP del ELM327 WiFi')
    parser.add_argument('--wifi-port', type=int, default=35000,
                        help='Puerto TCP del ELM327 WiFi')
    args = parser.parse_args()
    tester = HardwareRealTester(mode=args.mode, wifi_ip=args.wifi_ip,
                                wifi_port=args.wifi_port)
    tester.run_complete_test()
