import core.warmup as w


def test_ollama_warmup_waits_out_a_cold_model_load(monkeypatch):
    # The point of warming Ollama is to take the model load off the first real
    # query. A cold load of a multi-GB model on a machine that has to page it in
    # takes minutes, so a 30s timeout meant the warmup timed out every single
    # start and the user paid the load anyway. It runs on a daemon thread off the
    # critical path, so waiting is free.
    captured = {}

    def fake_post(url, json=None, timeout=None, **kwargs):
        captured["timeout"] = timeout

    monkeypatch.setattr(w, "_post", fake_post)

    w._warm_ollama()

    assert captured["timeout"] >= 120


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
