# gauge_realista.py
# Widget de Gauge realista para integración en la app principal
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient, QBrush

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
