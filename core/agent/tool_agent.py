import json
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"


def decide_tool(query):

    prompt = f"""
You are an AI tool selector.

Available tools:

1. open_calculator
- Opens calculator

2. increase_volume
- Increases volume

3. decrease_volume
- Decreases volume

4. mute_volume
- Mutes volume

Rules:
- Return ONLY valid JSON
- No explanation
- If no tool needed:
{{"tool": "none"}}

User Request:
{query}
"""

    payload = {
        "model": "phi3",
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

        return parsed.get("tool", "none")

    except Exception as e:

        print(f"Tool Agent Error: {e}")

        return "none"