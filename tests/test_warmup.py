import core.warmup as w


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
