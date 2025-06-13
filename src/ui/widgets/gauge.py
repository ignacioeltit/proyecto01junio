"""
GaugeWidget: Widget de gauge animado para PyQt6
Inspirado en dashboards automotrices modernos.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QRadialGradient
from PySide6.QtCore import Qt, QRectF, QTimer, QPointF
import math


class GaugeWidget(QWidget):
    def __init__(
        self,
        min_value=0,
        max_value=8000,
        units="RPM",
        color=QColor(0, 200, 255),
        parent=None,
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
        self.invalid = False  # Flag para indicar valor no numérico
        # Lista de valores no numéricos esperados (fácil de ampliar)
        self.non_numeric_values = {None, "", "NO DATA", "STOPPED", "\r>", "None"}

    def set_value(self, value):
        # ALTA COMPLEJIDAD: marcar para futura refactorización.
        # Conversión robusta a número o marca como inválido
        print(
            f"[DEBUG][GaugeWidget] set_value: valor recibido={value}"
        )
        self.invalid = False
        val_str = str(value).strip() if isinstance(value, str) else value
        if val_str in self.non_numeric_values:
            self.value = float(self.min_value)
            self._animated_value = float(self.min_value)
            self.invalid = True
            print(
                f"[DEBUG][GaugeWidget] Valor no numérico detectado: {value}"
            )
        else:
            try:
                if value is None:
                    self.value = float(self.min_value)
                    self._animated_value = float(self.min_value)
                    self.invalid = True
                elif isinstance(value, (int, float)):
                    v = max(self.min_value, min(self.max_value, float(value)))
                    if self.invalid:
                        self._animated_value = v
                    self.value = v
                    self.invalid = False
                elif isinstance(value, str):
                    if "." in value:
                        num = float(value)
                    else:
                        num = int(value)
                    v = max(self.min_value, min(self.max_value, num))
                    if self.invalid:
                        self._animated_value = v
                    self.value = v
                    self.invalid = False
                else:
                    self.value = float(self.min_value)
                    self._animated_value = float(self.min_value)
                    self.invalid = True
                    print(
                        f"[DEBUG][GaugeWidget] Tipo inesperado: {type(value)}"
                    )
            except Exception as e:  # noqa: E722
                self.value = float(self.min_value)
                self._animated_value = float(self.min_value)
                self.invalid = True
                print(
                    "[ADVERTENCIA][GaugeWidget] Error inesperado en set_value:",
                    e,
                )
        self.update()  # Forzar refresco inmediato
        print(
            f"[DEBUG][GaugeWidget] set_value: valor asignado={self.value}, "
            f"invalid={self.invalid}"
        )

    # Alias retrocompatible
    setValue = set_value

    def set_min_value(self, min_value):
        try:
            self.min_value = float(min_value)
        except Exception:
            self.min_value = 0

    def set_max_value(self, max_value):
        try:
            self.max_value = float(max_value)
        except Exception:
            self.max_value = 100

    def _animate(self):
        # Animación suave hacia el valor objetivo
        delta = self.value - self._animated_value
        if abs(delta) > 1:
            self._animated_value += delta * 0.15
            self.update()
        else:
            self._animated_value = self.value
            self.update()

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(10, 10, self.width() - 20, self.height() - 20)
        # Fondo con gradiente radial
        grad = QRadialGradient(rect.center(), rect.width() / 2)
        grad.setColorAt(0, QColor(40, 44, 54))
        grad.setColorAt(1, QColor(20, 22, 28))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(rect)
        # Escala y ticks
        num_ticks = 9
        tick_len = 12
        tick_color = QColor(120, 120, 120)
        font_ticks = QFont("Arial", 9)
        painter.setFont(font_ticks)
        for i in range(num_ticks):
            angle = 225 - i * 270 / (num_ticks - 1)
            rad = math.radians(angle)
            x1 = rect.center().x() + (rect.width() / 2 - 18) * math.cos(rad)
            y1 = rect.center().y() - (rect.height() / 2 - 18) * math.sin(rad)
            x2 = rect.center().x() + (rect.width() / 2 - 6) * math.cos(rad)
            y2 = rect.center().y() - (rect.height() / 2 - 6) * math.sin(rad)
            painter.setPen(QPen(tick_color, 2))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            # Valor numérico
            val = int(self.min_value + i * (self.max_value - self.min_value) / (num_ticks - 1))
            tx = rect.center().x() + (rect.width() / 2 - 32) * math.cos(rad)
            ty = rect.center().y() - (rect.height() / 2 - 32) * math.sin(rad)
            painter.setPen(QColor(180, 180, 180))
            painter.drawText(int(tx) - 12, int(ty) + 6, 24, 14, Qt.AlignmentFlag.AlignCenter, str(val))
        # Arco gauge (color dinámico)
        start_angle = 225
        span_angle = 270
        percent = 0
        if not self.invalid:
            percent = (self._animated_value - self.min_value) / (
                self.max_value - self.min_value
            )
            percent = max(0, min(1, percent))
            # Color dinámico
            if percent < 0.6:
                arc_color = QColor(60, 220, 60)  # Verde
            elif percent < 0.85:
                arc_color = QColor(255, 200, 40)  # Amarillo
            else:
                arc_color = QColor(255, 60, 60)  # Rojo
            pen = QPen(arc_color, 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(
                rect,
                int((start_angle - span_angle * percent) * 16),
                int(span_angle * percent * 16),
            )
        # Aguja tipo velocímetro
        if not self.invalid:
            angle = math.radians(225 - 270 * percent)
            needle_len = rect.width() / 2 - 32
            x = rect.center().x() + needle_len * math.cos(angle)
            y = rect.center().y() - needle_len * math.sin(angle)
            painter.setPen(QPen(QColor(220, 220, 220), 4))
            painter.drawLine(rect.center(), QPointF(x, y))
            # Centro de la aguja
            painter.setBrush(QColor(180, 180, 180))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect.center(), 8, 8)
        # Texto valor
        painter.setPen(QColor(240, 240, 240) if not self.invalid else QColor(255, 80, 80))
        font = QFont("Consolas", 32, QFont.Weight.Bold)
        painter.setFont(font)
        value_str = "---" if self.invalid else f"{int(self._animated_value):,}"
        painter.drawText(
            rect,
            int(Qt.AlignmentFlag.AlignCenter),
            str(value_str)
        )
        # Unidades
        font2 = QFont("Arial", 14)
        painter.setFont(font2)
        painter.setPen(QColor(180, 180, 180))
        painter.drawText(
            rect.adjusted(0, 60, 0, 0),
            int(Qt.AlignmentFlag.AlignHCenter),
            str(self.units)
        )
