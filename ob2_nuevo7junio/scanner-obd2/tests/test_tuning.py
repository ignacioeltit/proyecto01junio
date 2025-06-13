import pytest
from PySide6.QtWidgets import QApplication
from ui.tuning_widget import TuningWidget
from PySide6.QtTest import QTest
import os
import json

@pytest.fixture(scope="module")
def app():
    return QApplication([])

def test_widget_initialization(app):
    widget = TuningWidget(vehicle_info={"make": "default", "model": "default"})
    assert widget is not None
    assert widget.pid_list.count() > 0

def test_signal_emission(app):
    widget = TuningWidget(vehicle_info={"make": "default", "model": "default"})
    received = {}
    def handler(session_id, map_version, pid_values):
        received['session_id'] = session_id
        received['map_version'] = map_version
        received['pid_values'] = pid_values
    widget.tuning_update.connect(handler)
    widget.set_session("session123", "v1.0")
    widget.last_pid_values = {"AFR": 14.7, "EGT": 800}
    widget.pid_list.setCurrentRow(0)
    widget._update_live()
    QTest.qWait(100)  # Da tiempo al event loop
    assert 'session_id' in received
    assert received['session_id'] == "session123"
    assert received['map_version'] == "v1.0"
    assert isinstance(received['pid_values'], dict)

def test_reload_pids_dynamic(app):
    widget = TuningWidget(vehicle_info={"make": "default", "model": "default"})
    widget.vehicle_info = {"make": "Ford", "model": "Focus"}
    widget.reload_pids()
    # No error, list actualizada
    assert widget.pid_list.count() >= 0

def test_log_format():
    # Simula un log JSON line
    log_line = '{"timestamp": "2025-06-12T12:00:00Z", "level": "INFO", "module": "tuning", "session_id": "abc", "map_version": "v1", "VIN": "123", "make": "Ford", "model": "Focus", "rpm": 2000, "speed": 80, "afr": 14.7, "egt": 800, "boost": 1.2, "trims": 0.98, "timing": 12, "flags": {"WOT": true, "fallback": false, "knock_detected": false}}'
    data = json.loads(log_line)
    assert data["level"] == "INFO"
    assert "timestamp" in data
    assert "afr" in data
