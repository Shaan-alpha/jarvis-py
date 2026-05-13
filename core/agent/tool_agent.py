import json
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


def decide_tool(query):

    prompt = f"""
You are an AI tool selector.

Available tools:

{_tool_list_text()}

Rules:
- Return ONLY valid JSON
- No explanation
- If no tool needed:
{{"tool": "none"}}

User Request:
{query}
"""

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

        text = data["response"].strip()

        text = text.replace("```json", "")
        text = text.replace("```", "")

        parsed = json.loads(text)

        tool = parsed.get("tool", "none")

        if tool != "none" and tool not in TOOLS:

            return "none"

        return tool

    except Exception as e:

        logger.exception(
            f"Tool Agent Error: {e}"
        )

        return "none"
