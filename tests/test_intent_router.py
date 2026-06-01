from core.router.intent_router import route_intent

from core.intents.app_control import handle_app_control
from core.intents.media_control import handle_media_control
from core.intents.system_status import handle_system_status
from core.intents.browser import handle_browser


def test_app_control_phrases_route_to_app_handler():
    for query in ("open calculator", "close notepad", "open paint"):
        assert route_intent(query) is handle_app_control


def test_media_control_phrases_route_to_media_handler():
    for query in ("volume up", "increase volume", "mute", "decrease volume"):
        assert route_intent(query) is handle_media_control


def test_browser_phrases_route_to_browser_handler():
    for query in ("open google", "open edge"):
        assert route_intent(query) is handle_browser


def test_system_status_phrases_route_to_status_handler():
    for query in ("system status", "cpu usage", "battery level"):
        assert route_intent(query) is handle_system_status


def test_substring_match_inside_a_sentence_still_routes():
    # route_intent uses substring containment, so an embedded keyword matches.
    assert route_intent("hey can you open notepad for me") is handle_app_control


def test_unmatched_query_returns_none():
    # Falls through to the tool agent / LLM in the real pipeline.
    for query in ("what is python", "tell me a joke", "open spotify"):
        assert route_intent(query) is None
