from core.intents.app_control import handle_app_control
from core.intents.media_control import handle_media_control
from core.intents.system_status import handle_system_status
from core.intents.browser import handle_browser


def route_intent(query):

    # App Control
    if any(word in query for word in [
        "open",
        "close"
    ]):
        return handle_app_control

    # Media Control
    elif any(word in query for word in [
        "volume",
        "mute"
    ]):
        return handle_media_control

    # Browser
    elif any(word in query for word in [
        "google",
        "edge",
        "browser"
    ]):
        return handle_browser

    # System Status
    elif any(word in query for word in [
        "system condition",
        "battery",
        "cpu"
    ]):
        return handle_system_status

    return None