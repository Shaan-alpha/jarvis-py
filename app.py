import sys
import pyautogui

from core.speech.engine import speak, command
from core.utils.helpers import wishMe
from core.commands.handlers import social_media, schedule, browsing
from core.automation.system import openApp, closeApp, condition
from core.llm.ollama_engine import ask_llm


def handle_volume(query):
    if any(v in query for v in ["volume up", "increase volume"]):
        pyautogui.press("volumeup")
        speak("Volume increased")
        return True

    elif any(v in query for v in ["volume down", "decrease volume"]):
        pyautogui.press("volumedown")
        speak("Volume decreased")
        return True

    elif any(v in query for v in ["volume mute", "mute the sound"]):
        pyautogui.press("volumemute")
        speak("Volume muted")
        return True

    return False


def handle_apps(query):
    if any(app in query for app in [
        "open calculator",
        "open notepad",
        "open paint"
    ]):
        openApp(query, speak)
        return True

    elif any(app in query for app in [
        "close calculator",
        "close notepad",
        "close paint"
    ]):
        closeApp(query, speak)
        return True

    return False


def handle_system(query):
    if any(sys_c in query for sys_c in [
        "system condition",
        "condition of the system"
    ]):
        speak("Checking the system condition")
        condition(speak)
        return True

    return False


def handle_browser(query):
    if any(br in query for br in [
        "open google",
        "open edge"
    ]):
        browsing(query, speak, command)
        return True

    return False


def handle_social(query):
    if any(sm in query for sm in [
        "facebook",
        "discord",
        "whatsapp",
        "instagram",
        "youtube"
    ]):
        social_media(query, speak)
        return True

    return False


def handle_schedule(query):
    if any(sch in query for sch in [
        "university time table",
        "schedule"
    ]):
        schedule(speak)
        return True

    return False


def main():
    wishMe(speak)

    while True:
        query = command().lower().strip()

        if query == "none":
            continue

        print(f"User: {query}")

        # Exit
        if "exit" in query:
            speak("Goodbye Boss!")
            sys.exit()

        # Command handlers
        handled = (
            handle_social(query)
            or handle_schedule(query)
            or handle_volume(query)
            or handle_apps(query)
            or handle_browser(query)
            or handle_system(query)
        )

        # Fallback to LLM
        if not handled:
            speak("Thinking...")

            response = ask_llm(query)

            print(f"Jarvis: {response}")

            speak(response)


if __name__ == "__main__":
    main()