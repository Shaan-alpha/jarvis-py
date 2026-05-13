# pyrefly: ignore [missing-import]
from core.intents.app_control import handle_app_control
# pyrefly: ignore [missing-import]
from core.intents.media_control import handle_media_control
# pyrefly: ignore [missing-import]
from core.intents.system_status import handle_system_status
# pyrefly: ignore [missing-import]
from core.intents.browser import handle_browser


def route_intent(query):

    # App control
    if any(word in query for word in [
        "open calculator",
        "open notepad",
        "open paint",
        "close calculator",
        "close notepad",
        "close paint"
    ]):
        return handle_app_control

    # Media control
    elif any(word in query for word in [
        "volume up",
        "increase volume",
        "volume down",
        "decrease volume",
        "mute",
        "volume mute"
    ]):
        return handle_media_control

    # Browser
    elif any(word in query for word in [
        "open google",
        "open edge"
    ]):
        return handle_browser

    # System status
    elif any(word in query for word in [
        "system condition",
        "condition of the system"
    ]):
        return handle_system_status

    return None