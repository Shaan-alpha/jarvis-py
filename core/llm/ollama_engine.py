import requests

OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_llm(prompt):
    payload = {
        "model": "phi3",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            return response.json()["response"].strip()

        return "Sorry, I am having trouble reaching my brain right now."

    except Exception as e:
        print(f"Ollama Error: {e}")

        return (
            "I couldn't connect to the Ollama service. "
            "Please make sure it is running."
        )