"""
pid_acquisition.py - Módulo de adquisición de PIDs para Scanner OBD2
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import Qt

__all__ = ["PIDAcquisitionTab"]

class PIDAcquisitionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("<b>Adquisición de PIDs</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)
        self.info_label = QLabel("Esta pestaña permitirá adquirir y registrar datos de PIDs seleccionados en tiempo real.")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        self.start_btn = QPushButton("Iniciar adquisición")
        self.stop_btn = QPushButton("Detener adquisición")
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        self.setLayout(layout)

    def append_log(self, text):
        self.log_area.append(text)
