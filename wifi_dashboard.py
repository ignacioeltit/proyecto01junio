#!/usr/bin/env python3
import sys
import os

# Agregar ruta del proyecto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Función principal con manejo de errores"""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        try:
            from src.obd.elm327_wifi import ELM327WiFi
            from src.ui.widgets.wifi_status import WiFiStatusWidget
            print("✅ Módulos WiFi importados correctamente")
        except ImportError as e:
            print(f"❌ Error importando módulos WiFi: {e}")
            return
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
        class SimpleDashboard(QWidget):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("🚗 Dashboard WiFi Simple")
                self.setGeometry(200, 200, 600, 400)
                layout = QVBoxLayout()
                self.setLayout(layout)
                title = QLabel("🚗💨 Dashboard ELM327 WiFi")
                layout.addWidget(title)
                connect_btn = QPushButton("🔌 Probar Conexión WiFi")
                connect_btn.clicked.connect(self.test_connection)
                layout.addWidget(connect_btn)
                self.status_label = QLabel("Estado: Listo para conectar")
                layout.addWidget(self.status_label)
            def test_connection(self):
                try:
                    elm = ELM327WiFi()
                    if elm.connect():
                        self.status_label.setText("✅ Conectado al ELM327 WiFi")
                        data = elm.get_data() if hasattr(elm, 'get_data') else None
                        if data:
                            self.status_label.setText(f"✅ Datos: RPM={data.get('rpm', 0)}")
                        elm.disconnect()
                    else:
                        self.status_label.setText("❌ No se pudo conectar")
                except Exception as e:
                    self.status_label.setText(f"❌ Error: {e}")
        dashboard = SimpleDashboard()
        dashboard.show()
        print("✅ Dashboard WiFi iniciado")
        sys.exit(app.exec())
    except ImportError as e:
        print(f"❌ PyQt6 no está instalado: {e}")
        print("💡 Instala con: pip install PyQt6")
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
