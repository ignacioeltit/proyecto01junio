"""Entry point for the OBD-II scanner."""

from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from .core.config import Config
from .ui.gui import MainWindow


def main() -> None:
    config = Config.load()
    app = QApplication(sys.argv)
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
