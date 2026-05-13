import json
import re

import requests

from config.settings import (
    MODEL_NAME,
    OLLAMA_URL
)

from core.agent.tool_registry import (
    TOOLS
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


def _looks_like_action(query):

    q = query.strip().lower()

    return any(q.startswith(v) or f" {v}" in f" {q}" for v in ACTION_VERBS)


def _tool_list_text():

    lines = []

    for index, (name, meta) in enumerate(
        TOOLS.items(),
        start=1
    ):

        lines.append(
            f"{index}. {name}\n- {meta['description']}"
        )

    return "\n\n".join(lines)


def _extract_first_json(text):

    text = text.strip()

    text = text.replace("```json", "")

    text = text.replace("```", "")

    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)

    if not match:

        return None

    try:

        return json.loads(match.group(0))

    except json.JSONDecodeError:

        return None


def decide_tool(query):

    if not _looks_like_action(query):

        return "none"

    prompt = f"""You are a strict tool selector. Map the user's request
to exactly one of the available tool names, OR return "none" if the
request is not an explicit command to perform one of these actions.

Available tools:
{_tool_list_text()}

Strict rules:
- Output ONE JSON object only. No prose, no markdown, no extra text.
- Only return a tool name if the user is explicitly asking to perform
  that action right now.
- Questions, explanations, conversation, vague requests, anything
  containing "what", "why", "how", "explain", "tell me", "describe"
  -> return {{"tool": "none"}}.
- If unsure, return {{"tool": "none"}}.

Examples:
- "open the calculator" -> {{"tool": "open_calculator"}}
- "increase the volume please" -> {{"tool": "increase_volume"}}
- "mute the system" -> {{"tool": "mute_volume"}}
- "what is python" -> {{"tool": "none"}}
- "explain transformers in two lines" -> {{"tool": "none"}}
- "how is the weather" -> {{"tool": "none"}}

User Request:
{query}

JSON:"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
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
                f"Tool agent returned unparseable text: "
                f"{text[:120]!r}"
            )

            return "none"

        tool = parsed.get("tool", "none")

        if not isinstance(tool, str):

            return "none"

        tool = tool.strip().lower()

        if tool in ("", "none", "null"):

            return "none"

        if tool not in TOOLS:

            logger.info(
                f"Tool agent picked unknown tool {tool!r}, "
                f"falling back to LLM chat"
            )

            return "none"

        return tool

    except Exception as e:

        logger.exception(
            f"Tool Agent Error: {e}"
        )

        return "none"
