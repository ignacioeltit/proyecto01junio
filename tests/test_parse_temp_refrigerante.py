from src.obd.pids_ext import parse_temp_refrigerante


def test_parse_temp_refrigerante():
    assert parse_temp_refrigerante("41 05 7B") == 83
    assert parse_temp_refrigerante("41057B") == 83
    assert parse_temp_refrigerante("") is None
    assert parse_temp_refrigerante(None) is None
    assert parse_temp_refrigerante("41 05 XX") is None


if __name__ == "__main__":
    test_parse_temp_refrigerante()
    print("Test parse_temp_refrigerante OK")
