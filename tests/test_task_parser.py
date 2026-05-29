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
