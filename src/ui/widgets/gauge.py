"""
GaugeWidget: Widget de gauge animado para PyQt6
Inspirado en dashboards automotrices modernos.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QRectF, QTimer
import math


class GaugeWidget(QWidget):
    def __init__(
        self, min_value=0, max_value=8000, units="RPM",
        color=QColor(0, 200, 255), parent=None
    ):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.value = min_value
        self.units = units
        self.color = color
        self.setMinimumSize(200, 200)
        self._animated_value = min_value
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)  # ~60 FPS

    def setValue(self, value):
        print(f'[DEBUG][GaugeWidget] setValue: valor recibido={value}')
        print(f'[DEBUG][GaugeWidget] min={self.min_value}')
        print(f'[DEBUG][GaugeWidget] max={self.max_value}')
        print(f'[DEBUG][GaugeWidget] units={self.units}')
        self.value = max(self.min_value, min(self.max_value, value))
        self.update()  # Forzar refresco inmediato
        print(f'[DEBUG][GaugeWidget] setValue: valor asignado={self.value}')

    def _animate(self):
        # Animación suave hacia el valor objetivo
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
        rect = QRectF(10, 10, self.width()-20, self.height()-20)
        # Fondo
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 34, 40))
        painter.drawEllipse(rect)
        # Arco gauge
        start_angle = 225
        span_angle = 270
        percent = (self._animated_value - self.min_value) / \
            (self.max_value - self.min_value)
        angle = span_angle * percent
        pen = QPen(self.color, 18)
        painter.setPen(pen)
        painter.drawArc(rect, int((start_angle-angle)*16), int(angle*16))
        # Texto valor
        painter.setPen(QColor(240, 240, 240))
        font = QFont('Consolas', 32, QFont.Weight.Bold)
        painter.setFont(font)
        value_str = f"{int(self._animated_value):,}"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, value_str)
        # Unidades
        font2 = QFont('Arial', 14)
        painter.setFont(font2)
        painter.drawText(
            rect.adjusted(0, 60, 0, 0),
            Qt.AlignmentFlag.AlignHCenter,
            self.units
        )
