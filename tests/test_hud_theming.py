from core.hud.theming import theme_for_hour


def test_late_night_is_frost():
    assert theme_for_hour(4) == "frost"


def test_day_start_is_cyan():
    assert theme_for_hour(5) == "cyan"
    assert theme_for_hour(16) == "cyan"


def test_evening_is_gold():
    assert theme_for_hour(17) == "gold"
    assert theme_for_hour(20) == "gold"


def test_night_is_frost():
    assert theme_for_hour(21) == "frost"
    assert theme_for_hour(23) == "frost"
    assert theme_for_hour(0) == "frost"
