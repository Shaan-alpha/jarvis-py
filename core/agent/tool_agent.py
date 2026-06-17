import json

import re

import requests

from config.settings import (
    MODEL_NAME,
    OLLAMA_URL
)

from core.agent import (
    registry
)

from core.utils.logger import (
    logger
)


ACTION_VERBS = (
    "open ",
    "launch ",
    "start ",
    "run ",
    "play ",
    "close ",
    "shut ",
    "kill ",
    "stop ",
    "increase ",
    "decrease ",
    "raise ",
    "lower ",
    "turn up ",
    "turn down ",
    "mute ",
    "unmute ",
    "volume ",
)


_GATE_MAX_WORDS = 6


def _looks_like_action(query):

    q = query.strip().lower()

    if any(q.startswith(v) or f" {v}" in f" {q}" for v in ACTION_VERBS):

        return True

    words = set(re.findall(r"[a-z0-9]+", q))

    # A bare tool-name-token match (e.g. "read", "file") only counts as a command
    # for short, command-shaped utterances. A long sentence that merely mentions
    # a tool word ("i read a book on the weekend") shouldn't pay an Ollama call.
    if len(words) > _GATE_MAX_WORDS:

        return False

    for spec in registry.all_tools():

        if words & set(spec.name.lower().split("_")):

            return True

    return False


def _tool_list_text():

    lines = []

    for index, spec in enumerate(registry.all_tools(), start=1):

        if spec.params:

            param_lines = []

            for pname, pspec in spec.params.items():

                req = "required" if pspec.required else "optional"

                param_lines.append(
                    f"     - {pname} ({pspec.type}, {req}): {pspec.desc}"
                )

            params_text = "\n   params:\n" + "\n".join(param_lines)

        else:

            params_text = "\n   params: none"

        lines.append(
            f"{index}. {spec.name}\n   - {spec.description}{params_text}"
        )

    return "\n\n".join(lines)


def _extract_first_json(text):

    text = text.replace("```json", "").replace("```", "")

    start = text.find("{")

    if start == -1:

        return None

    try:

        obj, _ = json.JSONDecoder().raw_decode(text[start:])

        return obj

    except json.JSONDecodeError:

        return None


def _build_call_from_parsed(parsed):
    """Validate a parsed {"tool", "args"} object into a ToolCall, or None."""

    name = parsed.get("tool", "none")

    if not isinstance(name, str):

        return None

    name = name.strip().lower()

    if name in ("", "none", "null"):

        return None

    spec = registry.get(name)

    if spec is None:

        logger.info(
            f"Tool agent picked unknown tool {name!r}; falling back to chat"
        )

        return None

    raw_args = parsed.get("args", {})

    if not isinstance(raw_args, dict):

        raw_args = {}

    args, error = registry.coerce_and_validate(spec, raw_args)

    if error:

        logger.info(f"Tool {name!r} arg error: {error}; falling back to chat")

        return None

    return registry.ToolCall(name=name, args=args)


def decide_tool(query, raw_query=None):

    if not _looks_like_action(query):

        return None

    # Gate on the normalized query, but show the model the RAW utterance so the
    # content it extracts (e.g. write_clipboard/write_file text) keeps its
    # original case and punctuation instead of the lowercased form.
    if raw_query is None:

        raw_query = query

    prompt = f"""You are a strict tool selector. Map the user's request to
exactly one of the available tools, OR return "none" if the request is not an
explicit command to perform one of these actions.

Available tools:
{_tool_list_text()}

Strict rules:
- Output ONE JSON object only. No prose, no markdown.
- Shape: {{"tool": "<name>", "args": {{...}}}}  OR  {{"tool": "none"}}.
- Fill "args" using the tool's declared params; take values from the user's words.
- Only choose a tool if the user is explicitly asking to perform it now.
- Questions, explanations, conversation, anything with "what"/"why"/"how"/
  "explain"/"tell me"/"describe" -> {{"tool": "none"}}.
- If unsure, return {{"tool": "none"}}.

Examples:
- "open notepad" -> {{"tool": "open_app", "args": {{"name": "notepad"}}}}
- "increase the volume please" -> {{"tool": "increase_volume", "args": {{}}}}
- "what is python" -> {{"tool": "none"}}

User Request:
{raw_query}

JSON:"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        # Tool selection only emits a tiny JSON object, so cap generation and pin
        # temperature: the model returns fast and deterministically instead of
        # rambling before we parse the first {...}. A real tail-latency win on the
        # action path (this call blocks before ask_llm even starts).
        "options": {
            "num_predict": 80,
            "temperature": 0,
        },
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=30
        )

        data = response.json()

        text = data.get("response", "")

        parsed = _extract_first_json(text)

        if parsed is None:

            logger.warning(
                f"Tool agent returned unparseable text: {text[:120]!r}"
            )

            return None

        return _build_call_from_parsed(parsed)

    except Exception as e:

        logger.exception(f"Tool Agent Error: {e}")

        return None
