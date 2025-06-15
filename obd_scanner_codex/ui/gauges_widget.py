"""Simple gauge widgets using PySide6."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QDial
from PySide6.QtCore import Qt


class Gauge(QWidget):
    """Circular gauge using QDial."""

    def __init__(self, title: str, maximum: int = 100, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dial = QDial()
        self.dial.setMinimum(0)
        self.dial.setMaximum(maximum)
        self.dial.setNotchesVisible(True)
        self.label = QLabel(title)
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(self.dial)
        layout.addWidget(self.label)

    def update_value(self, value: float) -> None:
        self.dial.setValue(int(value))
        self.label.setText(f"{value}")
