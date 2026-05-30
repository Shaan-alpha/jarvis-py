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

from core.memory.document_memory import (
    search_documents
)

from core.memory.profile_memory import (
    get_profile_context
)

from core.hud import events

from core.utils.logger import (
    logger
)


# Short greetings / chitchat should never trigger document or memory
# retrieval — a vague utterance can weakly match an indexed chunk (e.g. a
# resume) and a small model then confabulates around it.
_CHITCHAT = {
    "hi", "hello", "hey", "yo", "sup",
    "how are you", "how are you doing", "how's it going",
    "what's up", "whats up", "good morning", "good afternoon",
    "good evening", "thanks", "thank you", "ok", "okay",
    "cool", "nice", "bye", "goodbye", "who are you",
}


def _should_retrieve(prompt):
    """True when the query is substantial enough to warrant document/memory
    retrieval. Skips greetings and very short utterances so RAG doesn't fire
    on chitchat like 'how are you'."""

    cleaned = prompt.lower().strip().strip("?.!,")

    if cleaned in _CHITCHAT:

        return False

    # Single- or two-word utterances are almost never document questions.
    if len(cleaned.split()) < 3:

        return False

    return True


def ask_llm(prompt):

    # -------------------- #
    # PROFILE CONTEXT
    # -------------------- #

    profile_context = (
        get_profile_context()
    )

    retrieve = _should_retrieve(prompt)

    # -------------------- #
    # SEMANTIC MEMORY
    # -------------------- #

    memory = search_memory(prompt) if retrieve else None

    memory_context = ""

    if memory:

        memory_context = f"""
Relevant Memory:
User: {memory['user']}
Assistant: {memory['assistant']}
"""

    # -------------------- #
    # DOCUMENT MEMORY
    # -------------------- #

    document_context = search_documents(prompt) if retrieve else []

    document_block = ""

    if document_context:

        document_text = "\n".join(document_context)

        document_block = (
            f"\nRelevant Documents (only use if "
            f"the user's question is clearly about them):\n"
            f"{document_text}\n"
        )

    # -------------------- #
    # PROMPT
    # -------------------- #

    final_prompt = f"""You are Jarvis, a concise voice assistant.

User Profile:
{profile_context}
{memory_context}{document_block}
Rules:
- Answer the user's question directly. Two sentences max.
- Only use the User Profile or Relevant Documents if the user's
  question is clearly about them. Otherwise IGNORE them completely
  and answer from general knowledge.
- Do NOT invent details about projects, jobs, or tools that were
  not asked about.
- Speak naturally for voice playback. No markdown, no emojis.

User: {prompt}

Jarvis:"""

    payload = {
        "model": MODEL_NAME,
        "prompt": final_prompt,
        "stream": True
    }

    try:

        logger.info(
            "Sending request to Ollama"
        )

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

                    events.emit("assistant_token", text=token)

                    sentence_buffer += token

                    # -------------------- #
                    # STREAMING TTS
                    # -------------------- #

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

        # -------------------- #
        # LEFTOVER BUFFER
        # -------------------- #

        if sentence_buffer.strip():

            add_to_queue(
                sentence_buffer.strip()
            )

        print()

        logger.info(
            "LLM response completed"
        )

        events.emit("assistant_done", full_text=full_response.strip())

        return full_response.strip()

    except Exception as e:

        logger.exception(
            f"Ollama Error: {e}"
        )

        message = "I can't reach Ollama right now. Is it running?"

        # Already queued for speech above; return empty so the caller
        # does not speak it a second time.
        add_to_queue(message)

        return ""
