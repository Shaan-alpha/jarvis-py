import os

from core.utils.jsonio import read_json, write_json_atomic


def test_roundtrip(tmp_path):
    path = str(tmp_path / "data.json")
    write_json_atomic(path, {"a": 1, "b": [1, 2, 3]})
    assert read_json(path) == {"a": 1, "b": [1, 2, 3]}


def test_read_missing_returns_default(tmp_path):
    path = str(tmp_path / "nope.json")
    assert read_json(path, default=[]) == []
    assert read_json(path) is None


def test_read_corrupt_returns_default(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ not valid json", encoding="utf-8")
    assert read_json(str(path), default={}) == {}


def test_write_creates_parent_dirs(tmp_path):
    path = str(tmp_path / "nested" / "deep" / "data.json")
    write_json_atomic(path, {"ok": True})
    assert read_json(path) == {"ok": True}


def test_write_overwrites_and_leaves_no_temp(tmp_path):
    path = str(tmp_path / "data.json")
    write_json_atomic(path, {"v": 1})
    write_json_atomic(path, {"v": 2})
    assert read_json(path) == {"v": 2}
    # No stray .tmp files after a successful write.
    leftovers = [n for n in os.listdir(tmp_path) if n.endswith(".tmp")]
    assert leftovers == []
