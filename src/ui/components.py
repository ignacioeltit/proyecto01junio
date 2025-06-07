"""
Componentes de interfaz de usuario para el dashboard OBD-II
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QGridLayout, QCheckBox
)

class PIDCheckboxPanel(QGroupBox):
    """Panel de checkboxes para selección de PIDs"""
    def __init__(self, title: str, pids: dict) -> None:
        super().__init__(title)
        self.checkboxes = {}
        self.setup_ui(pids)

    def setup_ui(self, pids: dict) -> None:
        """Configura la interfaz del panel"""
        layout = QGridLayout()
        row = 0
        col = 0
        
        for pid, info in pids.items():
            checkbox = QCheckBox(f"{info['name']} ({info['unit']})")
            self.checkboxes[pid] = checkbox
            layout.addWidget(checkbox, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
        
        self.setLayout(layout)

    def get_selected_pids(self) -> list:
        """Retorna lista de PIDs seleccionados"""
        return [pid for pid, checkbox in self.checkboxes.items() 
                if checkbox.isChecked()]


class DataDisplayPanel(QGroupBox):
    """Panel para mostrar los valores de los PIDs"""
    def __init__(self, title: str, pids: dict) -> None:
        super().__init__(title)
        self.labels = {}
        self.setup_ui(pids)

    def setup_ui(self, pids: dict) -> None:
        """Configura la interfaz del panel"""
        layout = QGridLayout()
        row = 0
        col = 0
        
        for pid, info in pids.items():
            name_label = QLabel(f"{info['name']}:")
            value_label = QLabel("--")
            self.labels[pid] = value_label
            
            layout.addWidget(name_label, row, col * 2)
            layout.addWidget(value_label, row, col * 2 + 1)
            col += 1
            if col > 2:
                col = 0
                row += 1
                
        self.setLayout(layout)

    def update_value(self, pid: str, value: str) -> None:
        """Actualiza el valor mostrado para un PID"""
        if pid in self.labels:
            self.labels[pid].setText(value)
