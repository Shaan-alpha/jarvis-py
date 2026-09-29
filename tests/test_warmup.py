import pytest

import core.warmup as w


def test_ollama_warmup_waits_out_a_cold_model_load(monkeypatch):
    # A cold load of a multi-GB model takes minutes; the warmup runs on a daemon
    # thread off the critical path, so waiting is free.
    captured = {}

    def fake_post(url, json=None, timeout=None, **kwargs):
        captured["timeout"] = timeout

    monkeypatch.setattr(w, "_free_gb", lambda: 16.0)
    monkeypatch.setattr(w, "_post", fake_post)
    w._warm_ollama()
    assert captured["timeout"] >= 120


def test_warmup_skips_the_model_preload_when_ram_is_short(monkeypatch):
    posted = []
    monkeypatch.setattr(w, "_free_gb", lambda: 0.5)
    monkeypatch.setattr(w, "_post", lambda *a, **k: posted.append(k))
    with pytest.raises(RuntimeError):
        w._warm_ollama()
    assert posted == []


def test_warmup_uses_the_small_context_window(monkeypatch):
    captured = {}
    monkeypatch.setattr(w, "_free_gb", lambda: 16.0)
    monkeypatch.setattr(w, "_post", lambda url, json=None, timeout=None: captured.update(json))
    w._warm_ollama()
    assert captured["options"]["num_ctx"] == 2048
    assert captured["keep_alive"] == "10m"


def test_run_warmup_runs_all_tasks_in_order():
    ran = []
    tasks = (("a", lambda: ran.append("a")), ("b", lambda: ran.append("b")))
    warmed = w.run_warmup(tasks)
    assert ran == ["a", "b"]
    assert warmed == ["a", "b"]


def test_run_warmup_swallows_failures_and_continues():
    def boom():
        raise RuntimeError("nope")

    ran = []
    tasks = (("ok", lambda: ran.append("ok")), ("bad", boom), ("ok2", lambda: ran.append("ok2")))
    warmed = w.run_warmup(tasks)
    assert ran == ["ok", "ok2"]      # a failing task doesn't stop the rest
    assert warmed == ["ok", "ok2"]   # and isn't reported as warmed


def test_warm_start_runs_on_a_daemon_thread():
    ran = []
    tasks = (("x", lambda: ran.append("x")),)
    thread = w.warm_start(tasks)
    assert thread.daemon is True
    thread.join(timeout=2)
    assert ran == ["x"]
