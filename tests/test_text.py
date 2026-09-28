import pytest

from core.text import normalize, plural, spoken_filename


@pytest.mark.parametrize("raw,expected", [
    ("What's on my clipboard?", "whats on my clipboard"),
    ("Read notes.txt", "read notes.txt"),
    ("It costs 3.5 dollars.", "it costs 3.5 dollars"),
    ("Hello,   world!!", "hello world"),
    ("‘Quoted’ text", "quoted text"),
    ("my-file_name.v2.pdf", "my-file_name.v2.pdf"),
    ("...", ""),
    ("", ""),
    (None, ""),
])
def test_normalize(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("notes dot txt", "notes.txt"),
    ("report dot p d f", "report.pdf"),
    ("my resume dot docx", "my resume.docx"),
    ("notes dot txt please", "notes.txt please"),
    ("budget.xlsx", "budget.xlsx"),
])
def test_spoken_filename(raw, expected):
    assert spoken_filename(raw) == expected


def test_plural():
    assert plural(1, "minute") == "1 minute"
    assert plural(5, "minute") == "5 minutes"
    assert plural(0, "file") == "0 files"
