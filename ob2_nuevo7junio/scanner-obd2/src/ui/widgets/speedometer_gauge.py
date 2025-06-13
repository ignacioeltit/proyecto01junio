# SpeedometerGaugeWidget: Un velocímetro visual tipo automotriz para PySide6
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
import math

class SpeedometerGaugeWidget(QWidget):
    def __init__(self, label="SPEED", min_value=0, max_value=240, units="km/h", parent=None):
        super().__init__(parent)
        self.label = label
        self.units = units
        self.min_value = min_value
        self.max_value = max_value
        self._value = min_value
        self.setMinimumSize(220, 220)
        layout = QVBoxLayout(self)
        self.title = QLabel(f"{self.label}")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("color: #fff; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.title)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        self.value_label = QLabel(f"{self._value} {self.units}")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet("color: #fff; font-size: 22px; font-weight: bold;")
        layout.addWidget(self.value_label)
        self.setLayout(layout)
        self.setStyleSheet("background: #181818; border-radius: 16px;")

    def set_value(self, value):
        try:
            v = float(value)
        except Exception:
            v = self.min_value
        v = max(self.min_value, min(self.max_value, v))
        self._value = v
        self.value_label.setText(f"{v:.0f} {self.units}")
        self.update()

    def value(self):
        return self._value

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(10, 40, -10, -30)
        center = rect.center()
        radius = min(rect.width(), rect.height()) // 2
        # Fondo
        painter.setBrush(QColor("#222"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)
        # Escala tipo velocímetro
        for i in range(0, 181, 6):
            angle = 180 - i
            color = QColor("#00eaff") if i < 120 else QColor("#ffe600") if i < 156 else QColor("#ff2d2d")
            pen = QPen(color, 7 if i % 18 == 0 else 3)
            painter.setPen(pen)
            painter.drawArc(QRectF(center.x()-radius+8, center.y()-radius+8, 2*(radius-8), 2*(radius-8)), (angle+90)*16, -6*16)
        # Aguja
        percent = (self._value - self.min_value) / (self.max_value - self.min_value)
        angle = 180 - percent * 180
        painter.save()
        painter.translate(center)
        painter.rotate(angle)
        pen = QPen(QColor("#ff2222"), 6)
        painter.setPen(pen)
        painter.drawLine(0, 0, 0, -radius+28)
        painter.restore()
        # Centro de la aguja
        painter.setBrush(QColor("#fff"))
        painter.setPen(QPen(QColor("#888"), 2))
        painter.drawEllipse(center, 12, 12)
        # Números grandes
        painter.setPen(QColor("#fff"))
        font = QFont("Arial", 12)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        for i in range(0, 10):
            val = int(self.min_value + i * (self.max_value - self.min_value) / 9)
            a = 180 - i*20
            rad = math.radians(a)
            x = center.x() + (radius-38) * 0.85 * math.cos(rad)
            y = center.y() - (radius-38) * 0.85 * math.sin(rad)
            painter.drawText(QRectF(x-18, y-12, 36, 24), Qt.AlignmentFlag.AlignCenter, f"{val}")
        # Unidades
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(QRectF(center.x()-35, center.y()+radius//2, 70, 22), Qt.AlignmentFlag.AlignCenter, self.units)
