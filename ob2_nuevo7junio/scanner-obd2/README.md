# OBD2 Professional Scanner

A robust, modular, and extensible OBD-II diagnostic suite for automotive professionals and enthusiasts. Integrates real-time data acquisition, advanced DTC management, and a modern GUI for both real and simulated environments.

## 🚀 Main Objective
This application provides advanced OBD-II diagnostics, real-time vehicle data visualization, and DTC management. It supports ELM327 (WiFi/USB) and J2534 hardware interfaces, and can operate in both real and simulation modes. Designed for workshops, researchers, and power users.

## 🧱 General Architecture
- **GUI (PySide6/PyQt6):** Multi-tab interface for diagnostics, live data, DTCs, and realistic automotive gauges (GAUGES 2.0).
- **Backend Acquisition:** Modular support for ELM327 (WiFi/USB) and J2534 adapters. Async and multiprocess data streams.
- **PID Manager:** Centralized PID definition, grouping, and batch reading.
- **Async Logger:** Non-blocking, session-based JSON logging for all events and readings.
- **DTC Reader:** Reads, decodes, and clears DTCs with VIN-aware logic and suggestions.
- **ELM327 Simulator:** Integrated for offline development and demo mode.
- **Offline/Emulation Mode:** Full functionality without vehicle connection for testing and training.

## 📦 Folder Structure (Excerpt)
```
scanner-obd2/
├── src/
│   ├── main.py                # Main app entry point
│   ├── main_async.py          # Async backend runner
│   ├── ui/
│   │   ├── data_visualizer.py # Main GUI logic
│   │   └── widgets/
│   │       └── gauge_realista.py # Realistic gauge widget
│   ├── core/
│   │   └── elm327_interface.py   # ELM327 comms
│   ├── elm327_async.py       # Async ELM327 logic
│   ├── obd2_async_utils.py   # Async helpers
│   ├── diagnostico/
│   │   └── dtc_manager.py    # DTC backend
│   └── ...
├── demo_gauges.py            # Standalone gauge demo
├── requirements.txt          # Dependencies
└── ...
```

## ⚙️ Requirements
- Python 3.9+
- PySide6 / PyQt6
- pyqtgraph
- python-OBD
- qasync
- (Optional) J2534 Python bindings
- OS: Windows, macOS, or Linux

## 🧪 Installation
```bash
# Clone the repository
$ git clone <repo_url>
$ cd scanner-obd2

# (Recommended) Create a virtual environment
$ python3 -m venv venv
$ source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
$ pip install -r requirements.txt

# Run the app
$ python src/main.py
```

## 🖥️ Simulator vs Real Mode
- **Simulator:** Launch with the ELM327 simulator script or set the app to "Emulation" mode in the GUI. No hardware required.
- **Real Hardware:** Connect an ELM327 (WiFi/USB) or J2534 device. Configure connection parameters in the GUI or config file.
- **Switching Modes:** Use the GUI toggle or command-line flags. See `main.py` for details.

## 📊 Logging & Export
- All sessions are logged in `/logs/SESSION.json` (JSON format).
- Logs include VIN, all readings, DTC events, and user actions.
- Export tools/scripts available for CSV or custom formats.
- Logs can be used for post-analysis, reporting, or training.

## 💻 Testing & Maintenance
- Run all tests with:
  ```bash
  pytest tests/
  ```
- Follow PEP8 and use type hints for new code.
- Contribute via pull requests. Document new modules and update this README as needed.
- TODO: Add CI/CD and code coverage badges.

## 🔒 License
MIT License

---

_Built to be the ultimate open automotive scanner._
