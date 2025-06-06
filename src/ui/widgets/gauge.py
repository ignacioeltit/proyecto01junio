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
        # Fondo
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(30, 34, 40))
        painter.drawEllipse(rect)
        # Arco gauge (solo si el valor es válido)
        start_angle = 225
        span_angle = 270
        if not self.invalid:
            percent = (self._animated_value - self.min_value) / (
                self.max_value - self.min_value
            )
            pen = QPen(self.color, 18)
            painter.setPen(pen)
            painter.drawArc(
                rect,
                int((start_angle - span_angle * percent) * 16),
                int(span_angle * percent * 16),
            )
        # Texto valor
        painter.setPen(QColor(240, 240, 240))
        font = QFont("Consolas", 32, QFont.Weight.Bold)
        painter.setFont(font)
        if self.invalid:
            value_str = "---"
            # Opcional: color de advertencia
            painter.setPen(QColor(255, 80, 80))
        else:
            value_str = f"{int(self._animated_value):,}"
        # Usar la sobrecarga correcta: QRectF, int, str
        painter.drawText(
            rect,
            int(Qt.AlignmentFlag.AlignCenter),
            str(value_str)
        )
        # Unidades
        font2 = QFont("Arial", 14)
        painter.setFont(font2)
        painter.drawText(
            rect.adjusted(0, 60, 0, 0),
            int(Qt.AlignmentFlag.AlignHCenter),
            str(self.units)
        )
