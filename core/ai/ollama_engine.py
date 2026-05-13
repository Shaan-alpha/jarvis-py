import json
import requests

from config.settings import (
    MODEL_NAME,
    OLLAMA_URL
)

from core.speech.tts_queue import (
    add_to_queue
)

from core.memory.semantic_memory import (
    search_memory
)


def ask_llm(prompt):

    memory = search_memory(prompt)

    memory_context = ""

    if memory:

        memory_context = f"""
Relevant Memory:
User: {memory['user']}
Assistant: {memory['assistant']}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": f"""
You are Jarvis, a concise AI assistant.

{memory_context}

Rules:
- Keep answers short
- Speak naturally
- Avoid roleplay
- Avoid unnecessary explanations

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

        print(
            "Jarvis: ",
            end="",
            flush=True
        )

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

                    print(
                        token,
                        end="",
                        flush=True
                    )

                    full_response += token

                    sentence_buffer += token

                    if any(
                        punctuation in sentence_buffer
                        for punctuation in [
                            ".",
                            "!",
                            "?"
                        ]
                    ):

                        add_to_queue(
                            sentence_buffer.strip()
                        )

                        sentence_buffer = ""

                except json.JSONDecodeError:

                    continue

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