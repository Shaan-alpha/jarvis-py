import core.setup.checks as checks


def test_select_returns_default_when_input_capable():
    devices = [
        {"index": 0, "maxInputChannels": 0},
        {"index": 1, "maxInputChannels": 2},
    ]
    assert checks.select_input_device(devices, default_index=1) == 1


def test_select_falls_back_to_first_input():
    devices = [
        {"index": 0, "maxInputChannels": 0},
        {"index": 2, "maxInputChannels": 1},
    ]
    assert checks.select_input_device(devices, default_index=0) == 2


def test_select_returns_none_when_no_input():
    devices = [{"index": 0, "maxInputChannels": 0}]
    assert checks.select_input_device(devices, default_index=0) is None
