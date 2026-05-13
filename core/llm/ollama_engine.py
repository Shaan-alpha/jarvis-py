import json
import requests

from core.speech.tts_queue import add_to_queue


OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_llm(prompt):

    payload = {
        "model": "phi3",
        "prompt": f"""
You are Jarvis, a concise AI assistant.

Rules:
- Keep answers short
- Speak naturally
- Avoid roleplay
- Avoid long explanations unless asked

User: {prompt}
Jarvis:
""",
        "stream": True
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=60
        )

        full_response = ""

        sentence_buffer = ""

        print("Jarvis: ", end="", flush=True)

        for line in response.iter_lines():

            if line:

                try:

                    data = json.loads(
                        line.decode("utf-8")
                    )

                    token = data.get(
                        "response",
                        ""
                    )

                    print(token, end="", flush=True)

                    full_response += token

                    sentence_buffer += token

                    # Speak complete sentence
                    if any(
                        punctuation in sentence_buffer
                        for punctuation in [".", "!", "?"]
                    ):

                        add_to_queue(
                            sentence_buffer.strip()
                        )

                        sentence_buffer = ""

                except json.JSONDecodeError:

                    continue

        # leftover text
        if sentence_buffer.strip():

            add_to_queue(
                sentence_buffer.strip()
            )

        print()

        return full_response.strip()

    except Exception as e:

        print(f"Ollama Error: {e}")

        return (
            "I couldn't connect to the Ollama service."
        )