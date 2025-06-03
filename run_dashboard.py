import sys
import os

# Añade src al sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SRC_PATH = os.path.join(BASE_DIR, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# Importa y ejecuta el dashboard principal
from ui.dashboard_gui import main

if __name__ == "__main__":
    main()
