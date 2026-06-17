import model_bakeoff as mb


def test_selection_prompt_includes_query_and_tools():
    p = mb.selection_prompt("open notepad", "1. open_app\n   - Open an app")
    assert "open notepad" in p
    assert "open_app" in p
    assert "JSON:" in p


def test_predicted_tool_parses_name():
    assert mb.predicted_tool('{"tool": "open_app", "args": {"name": "x"}}') == "open_app"
    assert mb.predicted_tool('noise {"tool":"SEARCH_WEB","args":{}} tail') == "search_web"


def test_predicted_tool_none_and_garbage():
    assert mb.predicted_tool('{"tool": "none"}') is None
    assert mb.predicted_tool("not json at all") is None
    assert mb.predicted_tool("") is None


def test_score_tool_case():
    assert mb.score_tool_case(None, None) is True
    assert mb.score_tool_case("open_app", "open_app") is True
    assert mb.score_tool_case("open_app", None) is False
    assert mb.score_tool_case(None, "open_app") is False


def test_summarize_computes_accuracy():
    results = [
        {"correct": True, "latency_ms": 100.0},
        {"correct": True, "latency_ms": 200.0},
        {"correct": False, "latency_ms": 300.0},
        {"correct": False, "latency_ms": None},   # failed call: excluded from avg
    ]
    s = mb.summarize("phi3", results)
    assert s["model"] == "phi3"
    assert s["n"] == 4
    assert s["correct"] == 2
    assert round(s["accuracy"]) == 50
    assert round(s["avg_tool_ms"]) == 200      # mean of 100/200/300


def test_format_report_lists_models():
    summaries = [
        {"model": "phi3", "n": 12, "correct": 9, "accuracy": 75.0, "avg_tool_ms": 420.0},
        {"model": "qwen2.5:1.5b", "n": 12, "correct": 11, "accuracy": 91.0, "avg_tool_ms": 180.0},
    ]
    chat_stats = {"phi3": {"avg_ttft_ms": 600.0, "avg_total_ms": 1800.0}}
    report = mb.format_report(summaries, chat_stats)
    assert "phi3" in report
    assert "qwen2.5:1.5b" in report
    assert "MODEL BAKE-OFF" in report


def test_is_installed_matches_bare_and_exact():
    installed = {"phi3:latest", "qwen2.5:1.5b", "llama3.2:3b"}
    assert mb.is_installed("phi3", installed) is True          # bare -> :latest
    assert mb.is_installed("qwen2.5:1.5b", installed) is True  # exact tag
    assert mb.is_installed("mistral", installed) is False


def test_installed_models_tolerates_unreachable():
    def boom(url, timeout=0):
        raise OSError("down")
    assert mb.installed_models(get=boom) == set()
