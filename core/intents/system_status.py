from core.automation.system import condition


def handle_system_status(query, speak):

    speak("Checking system condition")

    condition(speak)