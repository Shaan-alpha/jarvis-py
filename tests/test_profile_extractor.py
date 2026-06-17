from core.memory.profile_extractor import extract_personal_info


def test_extracts_name():
    result = extract_personal_info("my name is Tony Stark")
    assert result == {"key": "name", "value": "tony stark"}


def test_extracts_favorite_language():
    result = extract_personal_info(
        "my favorite programming language is python"
    )
    assert result == {"key": "favorite_language", "value": "python"}


def test_extracts_goal():
    result = extract_personal_info("i am preparing for my exams")
    assert result == {"key": "goal", "value": "my exams"}


def test_extracts_likes():
    result = extract_personal_info("i like building robots")
    assert result == {"key": "likes", "value": "building robots"}


def test_returns_none_for_plain_query():
    assert extract_personal_info("open the calculator") is None


def test_name_stops_at_clause_boundary():
    result = extract_personal_info("my name is tony and i like pizza")
    assert result == {"key": "name", "value": "tony"}


def test_value_is_length_capped():
    long_tail = "x" * 200
    result = extract_personal_info(f"i like {long_tail}")
    assert result["key"] == "likes"
    assert len(result["value"]) <= 60
