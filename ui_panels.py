from PyQt6.QtWidgets import QGroupBox, QGridLayout, QCheckBox

class PIDCheckboxPanel(QGroupBox):
    """Panel de checkboxes para selección de PIDs"""
    def __init__(self, title: str, pids: dict) -> None:
        super().__init__(title)
        self.checkboxes = {}
        self.setup_ui(pids)
    def setup_ui(self, pids: dict) -> None:
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
        return [pid for pid, checkbox in self.checkboxes.items() if checkbox.isChecked()]
