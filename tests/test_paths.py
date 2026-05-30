import sys

import core.paths as paths


def test_is_frozen_false_by_default(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert paths.is_frozen() is False


def test_is_frozen_true_when_sys_frozen_set(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert paths.is_frozen() is True
