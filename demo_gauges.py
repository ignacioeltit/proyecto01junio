# demo_gauges.py
# Demo visual de 3 estilos de GaugeWidget para PySide6
import sys
import math
import random
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget
from PySide6.QtCore import QTimer, Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient, QBrush

class GaugeWidget(QWidget):
    def __init__(self, label, min_value, max_value, units, color_style, style=1, parent=None):
        super().__init__(parent)
        self.label = label
        self.min_value = min_value
        self.max_value = max_value
        self.units = units
        self.value = min_value
        self.color_style = color_style  # QColor principal
        self.gauge_style = style  # 1: clásico, 2: moderno, 3: minimal
        self.setMinimumSize(220, 220)
        self.setMaximumSize(260, 260)
        self._animated_value = min_value
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)

    def set_value(self, value):
        try:
            v = float(value)
        except Exception:
            v = self.min_value
        v = max(self.min_value, min(self.max_value, v))
        self.value = v

    def _animate(self):
        delta = self.value - self._animated_value
        if abs(delta) > 1:
            self._animated_value += delta * 0.15
            self.update()
        else:
            self._animated_value = self.value
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(18, 18, -18, -18)
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2
        percent = (self._animated_value - self.min_value) / (self.max_value - self.min_value)
        percent = max(0, min(1, percent))
        # Fondo
        if self.gauge_style == 1:
            painter.setBrush(QColor("#181c24"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)
        elif self.gauge_style == 2:
            grad = QColor("#23272f")
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)
        else:
            painter.setBrush(QColor("#222"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)
        # Arco de valor
        pen = QPen(self.color_style, 18 if self.gauge_style != 3 else 10)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        start_angle = 225
        span_angle = 270 * percent
        painter.drawArc(rect, int((start_angle - span_angle) * 16), int(span_angle * 16))
        # Aguja (solo estilo 1 y 2)
        if self.gauge_style in (1, 2):
            angle = math.radians(225 - 270 * percent)
            needle_len = radius - 32
            x = center.x() + needle_len * math.cos(angle)
            y = center.y() - needle_len * math.sin(angle)
            painter.setPen(QPen(QColor("#fff"), 4))
            painter.drawLine(center, QPointF(x, y))
            painter.setBrush(QColor("#fff"))
            painter.setPen(QPen(QColor("#888"), 2))
            painter.drawEllipse(center, 8, 8)
        # Texto valor
        painter.setPen(QColor("#fff"))
        font = QFont("Arial", 32 if self.gauge_style != 3 else 28, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), f"{int(self._animated_value):,}")
        # Unidades
        font2 = QFont("Arial", 14)
        painter.setFont(font2)
        painter.setPen(QColor("#aaa"))
        painter.drawText(rect.adjusted(0, 60, 0, 0), int(Qt.AlignmentFlag.AlignHCenter), self.units)
        # Label
        font3 = QFont("Arial", 13, QFont.Weight.Bold)
        painter.setFont(font3)
        painter.setPen(self.color_style)
        painter.drawText(rect.adjusted(0, -60, 0, 0), int(Qt.AlignmentFlag.AlignHCenter), self.label)

class RealisticGaugeWidget(QWidget):
    def __init__(self, label, min_value, max_value, units, color_style, parent=None):
        super().__init__(parent)
        self.label = label
        self.min_value = min_value
        self.max_value = max_value
        self.units = units
        self.value = min_value
        self.color_style = color_style
        self.setMinimumSize(260, 260)
        self.setMaximumSize(320, 320)
        self._animated_value = min_value
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)

    def set_value(self, value):
        try:
            v = float(value)
        except Exception:
            v = self.min_value
        v = max(self.min_value, min(self.max_value, v))
        self.value = v

    def _animate(self):
        delta = self.value - self._animated_value
        if abs(delta) > 1:
            self._animated_value += delta * 0.15
            self.update()
        else:
            self._animated_value = self.value
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(20, 20, -20, -20)
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2
        percent = (self._animated_value - self.min_value) / (self.max_value - self.min_value)
        percent = max(0, min(1, percent))
        # Fondo metálico (gradiente radial gris metalizado)
        grad = QRadialGradient(center, radius)
        grad.setColorAt(0, QColor(220, 220, 220))
        grad.setColorAt(0.5, QColor(180, 180, 180))
        grad.setColorAt(0.8, QColor(120, 120, 120))
        grad.setColorAt(1, QColor(80, 80, 80))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect)
        # Contorno metálico realista
        contour_grad = QRadialGradient(center, radius)
        contour_grad.setColorAt(0, QColor(180, 180, 180, 180))
        contour_grad.setColorAt(0.7, QColor(120, 120, 120, 180))
        contour_grad.setColorAt(1, QColor(60, 60, 60, 255))
        pen = QPen(QBrush(contour_grad), 16)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(rect.adjusted(6, 6, -6, -6))
        # Efecto cristal (resalte blanco semitransparente)
        glass_rect = QRectF(rect.left()+18, rect.top()+10, rect.width()-36, rect.height()/2.2)
        glass_grad = QRadialGradient(glass_rect.center(), glass_rect.width()/2)
        glass_grad.setColorAt(0, QColor(255,255,255,120))
        glass_grad.setColorAt(1, QColor(255,255,255,0))
        painter.setBrush(glass_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(glass_rect)
        # Ticks y números
        painter.setPen(QPen(QColor(120, 120, 120), 2))
        font_ticks = QFont("Arial", 9)
        painter.setFont(font_ticks)
        num_ticks = 9
        for i in range(num_ticks):
            angle = 225 - i * 270 / (num_ticks - 1)
            rad = math.radians(angle)
            x1 = center.x() + (radius - 18) * math.cos(rad)
            y1 = center.y() - (radius - 18) * math.sin(rad)
            x2 = center.x() + (radius - 6) * math.cos(rad)
            y2 = center.y() - (radius - 6) * math.sin(rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            # Valor numérico
            val = int(self.min_value + i * (self.max_value - self.min_value) / (num_ticks - 1))
            tx = center.x() + (radius - 32) * math.cos(rad)
            ty = center.y() - (radius - 32) * math.sin(rad)
            painter.drawText(int(tx) - 12, int(ty) + 6, 24, 14, Qt.AlignmentFlag.AlignCenter, str(val))
        # Arco gauge (color dinámico)
        start_angle = 225
        span_angle = 270
        if percent < 0.6:
            arc_color = QColor(60, 220, 60)  # Verde
        elif percent < 0.85:
            arc_color = QColor(255, 200, 40)  # Amarillo
        else:
            arc_color = QColor(255, 60, 60)  # Rojo
        pen = QPen(arc_color, 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, int((start_angle - span_angle * percent) * 16), int(span_angle * percent * 16))
        # Aguja tipo velocímetro
        angle = math.radians(225 - 270 * percent)
        needle_len = radius - 32
        x = center.x() + needle_len * math.cos(angle)
        y = center.y() - needle_len * math.sin(angle)
        # Sombra de la aguja (detrás de la aguja y los números)
        painter.save()
        painter.setPen(QPen(QColor(80, 80, 80, 80), 8))
        painter.drawLine(center, QPointF(x, y))
        painter.restore()
        # Aguja principal
        painter.setPen(QPen(QColor(220, 220, 220), 4))
        painter.drawLine(center, QPointF(x, y))
        # Centro de la aguja
        painter.setBrush(QColor(240, 240, 240))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, 8, 8)
        # Texto valor
        painter.setPen(QColor(240, 240, 240))
        font = QFont("Consolas", 32, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), f"{int(self._animated_value):,}")
        # Unidades
        font2 = QFont("Arial", 14)
        painter.setFont(font2)
        painter.setPen(QColor(80, 80, 80))
        painter.drawText(rect.adjusted(0, 60, 0, 0), int(Qt.AlignmentFlag.AlignHCenter), self.units)
        # Label
        font3 = QFont("Arial", 13, QFont.Weight.Bold)
        painter.setFont(font3)
        painter.setPen(self.color_style)
        painter.drawText(rect.adjusted(0, -60, 0, 0), int(Qt.AlignmentFlag.AlignHCenter), self.label)

class DemoGaugesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo Gauges - 3 estilos")
        self.setStyleSheet("background: #181818;")
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        # Estilo 1: Clásico
        tab1 = QWidget()
        l1 = QHBoxLayout(tab1)
        self.g1 = GaugeWidget("RPM", 0, 8000, "rpm", QColor("#00eaff"), style=1)
        self.g2 = GaugeWidget("Velocidad", 0, 240, "km/h", QColor("#ffb300"), style=1)
        self.g3 = GaugeWidget("Temp Agua", 40, 120, "°C", QColor("#e91e63"), style=1)
        l1.addWidget(self.g1)
        l1.addWidget(self.g2)
        l1.addWidget(self.g3)
        tabs.addTab(tab1, "Clásico")
        # Estilo 2: Moderno
        tab2 = QWidget()
        l2 = QHBoxLayout(tab2)
        self.g4 = GaugeWidget("RPM", 0, 8000, "rpm", QColor("#00e676"), style=2)
        self.g5 = GaugeWidget("Velocidad", 0, 240, "km/h", QColor("#ff1744"), style=2)
        self.g6 = GaugeWidget("Temp Agua", 40, 120, "°C", QColor("#ffd600"), style=2)
        l2.addWidget(self.g4)
        l2.addWidget(self.g5)
        l2.addWidget(self.g6)
        tabs.addTab(tab2, "Moderno")
        # Estilo 3: Minimal
        tab3 = QWidget()
        l3 = QHBoxLayout(tab3)
        self.g7 = GaugeWidget("RPM", 0, 8000, "rpm", QColor("#2196f3"), style=3)
        self.g8 = GaugeWidget("Velocidad", 0, 240, "km/h", QColor("#ff9800"), style=3)
        self.g9 = GaugeWidget("Temp Agua", 40, 120, "°C", QColor("#43a047"), style=3)
        l3.addWidget(self.g7)
        l3.addWidget(self.g8)
        l3.addWidget(self.g9)
        tabs.addTab(tab3, "Minimal")
        # Estilo 4: Realista
        tab4 = QWidget()
        l4 = QHBoxLayout(tab4)
        self.r1 = RealisticGaugeWidget("RPM", 0, 8000, "rpm", QColor("#00eaff"))
        self.r2 = RealisticGaugeWidget("Velocidad", 0, 240, "km/h", QColor("#ffb300"))
        self.r3 = RealisticGaugeWidget("Temp Agua", 40, 120, "°C", QColor("#e91e63"))
        l4.addWidget(self.r1)
        l4.addWidget(self.r2)
        l4.addWidget(self.r3)
        tabs.addTab(tab4, "Realista")
        # Timer para animar valores demo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_gauges)
        self.timer.start(60)
        self.t = 0
    def update_gauges(self):
        self.t += 0.06
        # Simulación tipo onda y random
        self.g1.set_value(4000 + 3500 * math.sin(self.t))  # RPM
        self.g2.set_value(120 + 100 * math.sin(self.t/2))  # Velocidad
        self.g3.set_value(80 + 30 * math.sin(self.t/3))    # Temp Agua
        self.g4.set_value(4000 + 3500 * math.sin(self.t+1))
        self.g5.set_value(120 + 100 * math.sin(self.t/2+1))
        self.g6.set_value(80 + 30 * math.sin(self.t/3+1))
        self.g7.set_value(4000 + 3500 * math.sin(self.t+2))
        self.g8.set_value(120 + 100 * math.sin(self.t/2+2))
        self.g9.set_value(80 + 30 * math.sin(self.t/3+2))
        self.r1.set_value(4000 + 3500 * math.sin(self.t+3))
        self.r2.set_value(120 + 100 * math.sin(self.t/2+3))
        self.r3.set_value(80 + 30 * math.sin(self.t/3+3))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoGaugesWindow()
    win.resize(900, 320)
    win.show()
    sys.exit(app.exec())
