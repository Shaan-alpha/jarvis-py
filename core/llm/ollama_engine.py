import requests

from core.memory.memory_engine import load_memory

OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_llm(prompt):

    memory = load_memory()

    conversation_context = ""

    for chat in memory:

        conversation_context += (
            f"User: {chat['user']}\n"
            f"Assistant: {chat['assistant']}\n"
        )

    payload = {
        "model": "phi3",

        "prompt": f"""
You are Jarvis, a smart AI voice assistant.

Rules:
- Answer briefly and clearly.
- Maximum 2 sentences.
- Never roleplay.
- Never generate examples or instructions.
- Never continue conversations on your own.
- Never mention training data.
- Never mention Microsoft/OpenAI.
- Speak naturally like a real assistant.
- If user says hello, greet shortly.
- If user says bye, say goodbye shortly.

Previous conversation:
{conversation_context}

User: {prompt}

Jarvis:
""",

        "stream": False,

        "options": {
            "temperature": 0.4,
            "num_predict": 60
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:

            response_text = response.json()["response"].strip()

            # Cleanup garbage generations
            response_text = response_text.split("---")[0]
            response_text = response_text.split("Instruction:")[0]
            response_text = response_text.split("User:")[0]
            response_text = response_text.split("Assistant:")[0]
            response_text = response_text.split("Jarvis:")[0]

            response_text = response_text.strip()

            return response_text

        return "Sorry, I am having trouble reaching my brain right now."

    except Exception as e:

        print(f"Ollama Error: {e}")

        return (
            "I couldn't connect to the Ollama service. "
            "Please make sure it is running."
        )