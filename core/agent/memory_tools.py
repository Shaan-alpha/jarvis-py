"""Memory commands — remember, recall, "what's my X", forget. Router-only.

Forgetting always goes through a spoken confirmation (conversation.pending).
"""

import re

from core.agent.registry import (
    Reply,
    tool
)

from core.memory import facts

from core.memory.profile_memory import (
    delete_profile_key,
    load_profile
)

from core.state.conversation import (
    conversation
)


_EVERYTHING = {"everything", "all", "it all", "all of it", "everything you know"}

# First person as the user said it -> second person as Jarvis says it back.
_SECOND_PERSON = (
    (r"\bi am\b", "you are"),
    (r"\bim\b", "youre"),
    (r"\bmy\b", "your"),
    (r"\bmine\b", "yours"),
    (r"\bme\b", "you"),
    (r"\bi\b", "you"),
)


def second_person(text):

    for pattern, replacement in _SECOND_PERSON:

        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def profile_key(spoken):
    """'my favourite food' -> 'favourite_food'."""

    key = (spoken or "").strip().lower()

    if key.startswith("my "):

        key = key[3:]

    return "_".join(key.replace("favorite", "favourite").split())


def _profile_lookup(profile, key):
    """(stored key, value), accepting the older American spelling."""

    for candidate in (key, key.replace("favourite", "favorite")):

        if profile.get(candidate):

            return candidate, profile[candidate]

    return None, None


def _format(value):

    return ", ".join(value) if isinstance(value, list) else str(value)


@tool(
    "remember_fact",
    "Remember something the user asked Jarvis to remember",
    params={"text": {"type": "str", "required": True, "desc": "what to remember"}},
    llm=False,
)
def remember_fact(text):

    text = (text or "").strip(" .")

    if not text:

        return "What should I remember?"

    facts.add_fact(text)

    return Reply(say="Got it.", show=f"Remembered: {text}")


@tool("recall_memory", "Say what Jarvis remembers about the user", llm=False)
def recall_memory():

    items = [
        f"your {key.replace('_', ' ')} is {_format(value)}"
        for key, value in load_profile().items() if value
    ]

    newest = sorted(facts.all_facts(), key=lambda fact: fact.get("created", 0), reverse=True)

    items += [second_person(fact["text"]) for fact in newest[:5]]

    if not items:

        return "I don't have anything saved about you yet. Say 'remember that' and tell me something."

    return Reply(
        say="I remember: " + "; ".join(items[:3]) + ".",
        show="What I remember:\n" + "\n".join(f"- {item}" for item in items),
    )


@tool(
    "get_profile_value",
    "Answer 'what's my <name/city/...>' from the user profile",
    params={"key": {"type": "str", "required": True, "desc": "e.g. name, city"}},
    llm=False,
)
def get_profile_value(key):

    _, value = _profile_lookup(load_profile(), profile_key(key))

    if value is None:

        return f"You haven't told me your {key} yet."

    return f"Your {key} is {_format(value)}."


def _forget_everything():

    facts.clear_facts()

    return "Done. I've forgotten everything you asked me to remember."


# Confirmation callbacks always return a sentence: their result is spoken, so a
# bare `delete(...) and "..."` would read "False" aloud when nothing was deleted.
def _forget_profile(key, spoken):

    delete_profile_key(key)

    return f"Forgotten your {spoken}."


def _forget_fact(fact):

    facts.delete_fact(fact["id"])

    return "Forgotten."


@tool(
    "forget_memory",
    "Forget a remembered fact or profile detail (asks for confirmation)",
    params={"query": {"type": "str", "required": True, "desc": "what to forget"}},
    llm=False,
)
def forget_memory(query):

    spoken = (query or "").strip(" .").lower()

    if spoken in _EVERYTHING:

        conversation.set_pending("forget everything", _forget_everything)

        return "Forget everything you asked me to remember? Say yes to confirm."

    key, _ = _profile_lookup(load_profile(), profile_key(spoken))

    if key is not None:

        conversation.set_pending(f"forget {key}", lambda: _forget_profile(key, spoken))

        return f"Forget your {spoken}? Say yes to confirm."

    fact = facts.find_fact(spoken)

    if fact is None:

        return f"I don't have anything saved about {spoken}."

    conversation.set_pending(f"forget fact {fact['id']}", lambda: _forget_fact(fact))

    return Reply(
        say="Forget that? Say yes to confirm.",
        show=f"Forget: {fact['text']}?\nSay yes to confirm.",
    )
