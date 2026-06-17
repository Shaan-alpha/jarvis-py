"""Model bake-off: benchmark candidate local Ollama models for Jarvis.

Measures, per model:
  1. Tool-selection accuracy — does the model map labelled commands to the right
     registry tool (the decide_tool task)?
  2. Response latency — time-to-first-token (TTFT) and total time on chat prompts.

CI-safe to import (no I/O at import). Run it against a live Ollama:

    python model_bakeoff.py                      # default candidate set
    python model_bakeoff.py phi3 qwen2.5:1.5b    # explicit candidates

Candidates must be pulled first (`ollama pull <name>`); missing ones are skipped.
Quality is subjective, so each model's chat answers are printed for you to judge.
"""

import argparse
import json
import sys
import time

import requests

from config.settings import OLLAMA_URL, OLLAMA_TAGS_URL

from core.agent.loader import init_tools
from core.agent.tool_agent import _tool_list_text, _extract_first_json


DEFAULT_CANDIDATES = ["phi3", "phi3.5", "llama3.2:3b", "qwen2.5:1.5b"]

# (query, expected_tool_name or None) — None means "should pick no tool".
TOOL_CASES = [
    ("open notepad", "open_app"),
    ("launch the calculator", "open_app"),
    ("close notepad", "close_app"),
    ("increase the volume please", "increase_volume"),
    ("turn the volume down", "decrease_volume"),
    ("mute the sound", "mute_volume"),
    ("what's my cpu usage", "system_status"),
    ("read my clipboard", "read_clipboard"),
    ("search the web for python tutorials", "search_web"),
    ("what is the capital of france", None),
    ("explain how recursion works", None),
    ("tell me a joke", None),
]

CHAT_PROMPTS = [
    "What is the capital of Japan?",
    "Explain recursion in one sentence.",
    "Give me a two-sentence summary of photosynthesis.",
]


# -------------------- pure logic (unit-tested) -------------------- #


def selection_prompt(query, tools_text):
    """Mirror decide_tool's tool-selection prompt for a given query."""

    return f"""You are a strict tool selector. Map the user's request to
exactly one of the available tools, OR return "none" if the request is not an
explicit command to perform one of these actions.

Available tools:
{tools_text}

Strict rules:
- Output ONE JSON object only. No prose, no markdown.
- Shape: {{"tool": "<name>", "args": {{...}}}}  OR  {{"tool": "none"}}.
- Only choose a tool if the user is explicitly asking to perform it now.
- If unsure, return {{"tool": "none"}}.

User Request:
{query}

JSON:"""


def predicted_tool(text):
    """Parse a model's tool-selection output into a tool name, or None."""

    parsed = _extract_first_json(text or "")

    if not isinstance(parsed, dict):

        return None

    name = parsed.get("tool", "none")

    if not isinstance(name, str):

        return None

    name = name.strip().lower()

    if name in ("", "none", "null"):

        return None

    return name


def score_tool_case(expected, predicted):
    """True when the model's pick matches the label (None == 'no tool')."""

    return expected == predicted


def summarize(model, case_results):
    """Aggregate per-case results into a model summary (pure)."""

    n = len(case_results)

    correct = sum(1 for r in case_results if r["correct"])

    latencies = [r["latency_ms"] for r in case_results if r["latency_ms"] is not None]

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    accuracy = (correct / n * 100.0) if n else 0.0

    return {
        "model": model,
        "n": n,
        "correct": correct,
        "accuracy": accuracy,
        "avg_tool_ms": avg_latency,
    }


def format_report(summaries, chat_stats):
    """Render a compact comparison table (pure)."""

    header = (
        f"{'model':<18} {'tool-acc':>9} {'tool-ms':>9} "
        f"{'chat-ttft':>10} {'chat-total':>11}"
    )

    lines = ["", "=== MODEL BAKE-OFF ===", "", header, "-" * len(header)]

    for s in summaries:

        cs = chat_stats.get(s["model"], {})

        lines.append(
            f"{s['model']:<18} "
            f"{s['accuracy']:>7.0f}% "
            f"{s['avg_tool_ms']:>8.0f} "
            f"{cs.get('avg_ttft_ms', 0.0):>9.0f} "
            f"{cs.get('avg_total_ms', 0.0):>10.0f}"
        )

    return "\n".join(lines)


def is_installed(model, installed):
    """True if `model` matches an installed Ollama tag (bare name == :latest)."""

    if model in installed:

        return True

    if ":" not in model:

        return any(tag.split(":")[0] == model for tag in installed)

    return False


# -------------------- I/O (runs only against a live Ollama) -------------------- #


def installed_models(get=requests.get):

    try:

        resp = get(OLLAMA_TAGS_URL, timeout=3)

        return {m.get("name", "") for m in resp.json().get("models", [])}

    except Exception:

        return set()


def _generate(model, prompt):
    """Non-streaming completion (the tool-selection task). Returns text or None."""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 80, "temperature": 0},
    }

    try:

        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)

        return resp.json().get("response", "")

    except Exception as e:

        print(f"  ! {model} tool call failed: {e}")

        return None


def _stream_timed(model, prompt):
    """Streamed completion; returns (ttft_ms, total_ms, text)."""

    payload = {"model": model, "prompt": prompt, "stream": True}

    start = time.perf_counter()

    first = None

    text = ""

    try:

        resp = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120)

        for line in resp.iter_lines():

            if not line:

                continue

            token = json.loads(line.decode("utf-8")).get("response", "")

            if token and first is None:

                first = (time.perf_counter() - start) * 1000.0

            text += token

        return first, (time.perf_counter() - start) * 1000.0, text.strip()

    except Exception as e:

        print(f"  ! {model} chat failed: {e}")

        return None, None, ""


def run_tool_accuracy(model):

    tools_text = _tool_list_text()

    results = []

    for query, expected in TOOL_CASES:

        start = time.perf_counter()

        text = _generate(model, selection_prompt(query, tools_text))

        latency_ms = (time.perf_counter() - start) * 1000.0 if text is not None else None

        pred = predicted_tool(text)

        results.append({
            "query": query,
            "expected": expected,
            "predicted": pred,
            "correct": score_tool_case(expected, pred),
            "latency_ms": latency_ms,
        })

    return results


def run_chat_latency(model):

    ttfts, totals, answers = [], [], []

    for prompt in CHAT_PROMPTS:

        ttft, total, text = _stream_timed(model, prompt)

        if ttft is not None:

            ttfts.append(ttft)

            totals.append(total)

        answers.append((prompt, text))

    return {
        "avg_ttft_ms": sum(ttfts) / len(ttfts) if ttfts else 0.0,
        "avg_total_ms": sum(totals) / len(totals) if totals else 0.0,
        "answers": answers,
    }


def _print_detail(tool_results, chat):

    for r in tool_results:

        if not r["correct"]:

            print(f"   miss: {r['query']!r} -> got {r['predicted']!r}, want {r['expected']!r}")

    for prompt, ans in chat["answers"]:

        print(f"   Q: {prompt}\n   A: {ans}\n")


def _bench_model(model):

    print(f"\n[bench] {model} ...")

    tool_results = run_tool_accuracy(model)

    chat = run_chat_latency(model)

    _print_detail(tool_results, chat)

    return summarize(model, tool_results), chat


def main():

    parser = argparse.ArgumentParser(description="Benchmark Ollama models for Jarvis")

    parser.add_argument(
        "models",
        nargs="*",
        default=DEFAULT_CANDIDATES,
        help="model tags to benchmark (default: a small candidate set)",
    )

    args = parser.parse_args()

    candidates = args.models or DEFAULT_CANDIDATES

    init_tools()   # populate the registry so the tool list + scoring are real

    installed = installed_models()

    if not installed:

        print(f"Could not reach Ollama at {OLLAMA_URL} — is it running?")

        return 1

    summaries, chat_stats = [], {}

    for model in candidates:

        if not is_installed(model, installed):

            print(f"[skip] {model} not installed (ollama pull {model})")

            continue

        summary, chat = _bench_model(model)

        summaries.append(summary)

        chat_stats[model] = chat

    print(format_report(summaries, chat_stats))

    return 0


if __name__ == "__main__":

    sys.exit(main())
