"""Real-time plot widget using pyqtgraph."""

from __future__ import annotations

from collections import deque
from typing import Deque, List

from PySide6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg


class RealTimePlot(QWidget):
    """Plot values over time."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data: Deque[float] = deque(maxlen=100)
        self.plot_widget = pg.PlotWidget(title=title)
        self.curve = self.plot_widget.plot([])
        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_widget)

    def add_value(self, value: float) -> None:
        self.data.append(value)
        self.curve.setData(list(self.data))
