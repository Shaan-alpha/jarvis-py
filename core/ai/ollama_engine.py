import json
import re
import threading

from datetime import datetime

import requests

from config.settings import (
    LLM_KEEP_ALIVE,
    LLM_NUM_CTX,
    LLM_TEMPERATURE,
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

from core.ai import llm_health

from core.hud import events

from core.net import (
    is_online
)

from core.state.conversation import (
    conversation
)

from core.utils import metrics

from core.text import (
    normalize,
    spoken_date,
    spoken_time
)

from core.utils.logger import (
    logger
)


# Short greetings / chitchat should never trigger document or memory
# retrieval — a vague utterance can weakly match an indexed chunk (e.g. a
# resume) and a small model then confabulates around it.
_CHITCHAT = {
    normalize(phrase) for phrase in (
        "hi", "hello", "hey", "yo", "sup",
        "how are you", "how are you doing", "how's it going",
        "what's up", "good morning", "good afternoon",
        "good evening", "thanks", "thank you", "ok", "okay",
        "cool", "nice", "bye", "goodbye", "who are you",
    )
}


# Generation ceilings. The prompt asks for two sentences, but a small model does
# not reliably obey (unbounded, phi3 ran for minutes and scripted a whole new
# conversation aloud), so the stream is also cut after MAX_SPOKEN_SENTENCES.
REPLY_TOKEN_LIMIT = 96

DETAILED_TOKEN_LIMIT = 300

MAX_SPOKEN_SENTENCES = 2

DETAILED_SENTENCES = 6

# Turn markers a rambling model writes when it starts scripting a new dialogue.
REPLY_STOP_SEQUENCES = [
    "\nUser:", "\nInstruction:", "\nJarvis:", "\n###", "\nUser Profile:", "\nRules:",
]

# A sentence ends at . ! or ? (plus closing quotes/brackets) followed by
# whitespace — so "3.14" and "e.g.x" never split mid-number.
_SENTENCE_END = re.compile(r"[.!?]+[\"')\]]*(?=\s)")

_RULES = (
    "Rules:\n"
    "- If you are not sure, or it needs live data (news, prices, scores, weather), "
    "say you don't know. Never guess.\n"
    "- You cannot take actions. Never claim you opened, saved, set, sent or changed anything.\n"
    "- Use what you know about the user, remembered facts or documents only when "
    "the question is about them."
)


# Generation token for barge-in. Each ask_llm() call bumps the counter; an
# in-flight stream that finds a newer generation has started aborts itself, so
# a new query (typed or spoken) interrupts the previous answer instead of
# queueing behind it.
_generation_lock = threading.Lock()

_generation = 0


def _start_generation():

    global _generation

    with _generation_lock:

        _generation += 1

        return _generation


def _is_current(generation):

    return generation == _generation


def cancel_generation():
    """Abandon whatever answer is streaming now (Stop / Esc / a new query).

    Bumping the generation makes the in-flight stream fail its _is_current
    check on the next line: it closes the HTTP response, queues nothing more
    and skips assistant_done."""

    _start_generation()


def _should_retrieve(prompt):
    """True when the query is substantial enough to warrant document/memory
    retrieval. Skips greetings and very short utterances so RAG doesn't fire
    on chitchat like 'how are you'."""

    cleaned = normalize(prompt)

    if cleaned in _CHITCHAT:

        return False

    # Single- or two-word utterances are almost never document questions.
    if len(cleaned.split()) < 3:

        return False

    return True


def _clock():

    return datetime.now()


def _online():
    """Connectivity for the prompt. A recent cached answer is fine here."""

    return is_online(max_age=60)


def build_prompt(query, *, now, online, profile="", facts=(), documents=(), history=(), detailed=False):
    """The full grounded prompt. Pure (clock and connectivity passed in)."""

    length = (
        "Reply in up to six short sentences." if detailed
        else "Reply in one or two short sentences, under 30 words."
    )

    parts = [
        f"You are Jarvis, a voice assistant. {length}\n"
        f"Plain spoken English: no lists, markdown or emojis.",
        f"Now: {spoken_date(now)}, {spoken_time(now)}. "
        f"Internet: {'online' if online else 'offline'}.",
    ]

    if profile:

        parts.append(f"About the user:\n{profile}")

    if facts:

        parts.append("Things the user asked you to remember:\n" + "\n".join(f"- {f}" for f in facts))

    if documents:

        parts.append("Documents (use only if the question is about them):\n" + "\n".join(documents))

    if history:

        parts.append("Recent conversation:\n" + "\n".join(f"User: {u}\nJarvis: {r}" for u, r in history))

    parts.append(_RULES)

    parts.append(f"User: {query}\nJarvis:")

    return "\n\n".join(parts)


def _speak_error(message):
    """Say a failure out loud and show it in the HUD as an error."""

    events.emit("error", message=message)

    add_to_queue(message)


def _flush_sentences(buffer, spoken, max_sentences):
    """Queue each complete sentence in `buffer`; return the unfinished rest."""

    while len(spoken) < max_sentences:

        match = _SENTENCE_END.search(buffer)

        if not match:

            break

        sentence = buffer[:match.end()].strip()

        buffer = buffer[match.end():]

        if sentence:

            add_to_queue(sentence)

            metrics.mark("first_audio")

            spoken.append(sentence)

    return buffer


def _stream_response(response, my_generation, max_sentences=MAX_SPOKEN_SENTENCES):
    """Consume the streamed reply: emit tokens, queue whole sentences, stop at
    `max_sentences`. Returns exactly the spoken text, or None if a newer query
    superseded this stream (barge-in)."""

    spoken = []

    buffer = ""

    print("Jarvis: ", end="", flush=True)

    for line in response.iter_lines():

        # Barge-in: a newer query started — abandon this stream.
        if not _is_current(my_generation):

            logger.info("LLM stream superseded by a newer query")

            response.close()

            return None

        if not line:

            continue

        try:

            token = json.loads(line.decode("utf-8")).get("response", "")

        except json.JSONDecodeError:

            continue

        if not token:

            continue

        # Dedup keeps the first occurrence, so this records time-to-first-token.
        metrics.mark("first_token")

        print(token, end="", flush=True)

        events.emit("assistant_token", text=token)

        buffer = _flush_sentences(buffer + token, spoken, max_sentences)

        if len(spoken) >= max_sentences:

            # Hard cap: hang up so the rest is never generated, queued or shown.
            response.close()

            buffer = ""

            break

    # Superseded right as the stream ended.
    if not _is_current(my_generation):

        return None

    tail = buffer.strip()

    if tail and len(spoken) < max_sentences:

        add_to_queue(tail)

        metrics.mark("first_audio")

        spoken.append(tail)

    print()

    return " ".join(spoken)


def _build_payload(prompt, detailed):

    retrieve = _should_retrieve(prompt)

    memory = search_memory(prompt) if retrieve else None

    facts = [f"{memory['user']} -> {memory['assistant']}"] if memory else []

    final_prompt = build_prompt(
        prompt,
        now=_clock(),
        online=_online(),
        profile=get_profile_context(),
        facts=facts,
        documents=search_documents(prompt) if retrieve else [],
        history=conversation.history(),
        detailed=detailed,
    )

    return {
        "model": MODEL_NAME,
        "prompt": final_prompt,
        "stream": True,
        "keep_alive": LLM_KEEP_ALIVE,
        "options": {
            "num_predict": DETAILED_TOKEN_LIMIT if detailed else REPLY_TOKEN_LIMIT,
            "num_ctx": LLM_NUM_CTX,
            "temperature": LLM_TEMPERATURE,
            "top_p": 0.9,
            "stop": REPLY_STOP_SEQUENCES,
        },
    }


def _report_error_status(response):
    """Ollama answered with an error status (commonly 500 when the model needs
    more memory than is free). The body carries no tokens, so without this the
    user just hears silence."""

    detail = ""

    try:

        detail = (response.json() or {}).get("error", "") or ""

    except Exception:

        detail = (response.text or "")[:200]

    logger.error(f"Ollama returned {response.status_code}: {detail}")

    llm_health.mark_down(detail or f"HTTP {response.status_code}")

    if "memory" in detail.lower():

        _speak_error("I couldn't run the model — it needs more memory than is free right now.")

    else:

        _speak_error("Something went wrong running the model.")


def ask_llm(prompt, detailed=False):
    """Stream a grounded answer to `prompt`; returns exactly what was spoken,
    or "" (superseded, or the model is unavailable — already said aloud)."""

    # Claim a generation; a later query bumps this and supersedes us.
    my_generation = _start_generation()

    if llm_health.is_down():

        _speak_error(llm_health.unavailable_message())

        return ""

    payload = _build_payload(prompt, detailed)

    try:

        logger.info("Sending request to Ollama")

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=True,
            timeout=60
        )

        if not response.ok:

            _report_error_status(response)

            return ""

        full_response = _stream_response(
            response,
            my_generation,
            DETAILED_SENTENCES if detailed else MAX_SPOKEN_SENTENCES
        )

        # None = a newer query superseded this stream (barge-in); don't emit a
        # done event that would clobber the new answer.
        if full_response is None:

            return ""

        llm_health.mark_up()

        logger.info("LLM response completed")

        events.emit("assistant_done", full_text=full_response.strip())

        return full_response.strip()

    except Exception as e:

        logger.exception(f"Ollama Error: {e}")

        llm_health.mark_down(str(e))

        _speak_error("I can't reach Ollama right now. Is it running?")

        return ""
