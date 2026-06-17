from core.tasks.task_parser import parse_reminder


def test_parses_singular_minute():
    result = parse_reminder("remind me in 1 minute to stretch")
    assert result == {"minutes": 1, "message": "stretch"}


def test_parses_plural_minutes():
    result = parse_reminder("remind me in 10 minutes to drink water")
    assert result == {"minutes": 10, "message": "drink water"}


def test_is_case_insensitive():
    result = parse_reminder("REMIND ME IN 5 MINUTES TO call mom")
    assert result is not None
    assert result["minutes"] == 5
    assert result["message"] == "call mom"


def test_returns_none_for_non_reminder():
    assert parse_reminder("what is the weather today") is None


def test_returns_none_without_message():
    assert parse_reminder("remind me in 10 minutes") is None


def test_parses_hours():
    result = parse_reminder("remind me in 2 hours to stretch")
    assert result == {"minutes": 120, "message": "stretch"}


def test_parses_an_hour():
    result = parse_reminder("remind me in an hour to call mom")
    assert result == {"minutes": 60, "message": "call mom"}


def test_parses_half_an_hour():
    result = parse_reminder("remind me in half an hour to rest")
    assert result == {"minutes": 30, "message": "rest"}


def test_parses_seconds_as_fraction():
    result = parse_reminder("remind me in 90 seconds to check the oven")
    assert result["minutes"] == 1.5
    assert result["message"] == "check the oven"


def test_parses_reversed_word_order():
    result = parse_reminder("remind me to drink water in 15 minutes")
    assert result == {"minutes": 15, "message": "drink water"}


def test_short_form_minutes():
    result = parse_reminder("remind me in 5 mins to log off")
    assert result == {"minutes": 5, "message": "log off"}
