from core.automation.system import openApp, closeApp


def handle_app_control(query, speak):

    if "open" in query:
        openApp(query, speak)

    elif "close" in query:
        closeApp(query, speak)