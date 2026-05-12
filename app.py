import sys
import time

from core.speech.engine import speak, command
from core.utils.helpers import wishMe

from core.commands.handlers import (
    social_media,
    schedule,
    browsing
)

from core.automation.system import (
    openApp,
    closeApp,
    condition
)

from core.llm.ollama_engine import ask_llm
from core.memory.memory_engine import save_memory

import pyautogui


def main():

    wishMe(speak)

    while True:

        query = command().lower()

        if query == "none":
            time.sleep(1)
            continue

        print(f"User: {query}")

        # Exit Commands
        if any(word in query for word in [
            "exit",
            "bye",
            "goodbye",
            "shutdown",
            "stop"
        ]):
            speak("Goodbye Boss!")
            sys.exit()

        # Social Media
        elif any(sm in query for sm in [
            "facebook",
            "discord",
            "whatsapp",
            "instagram",
            "youtube"
        ]):
            social_media(query, speak)

        # Schedule
        elif any(sch in query for sch in [
            "schedule",
            "timetable"
        ]):
            schedule(speak)

        # Volume Controls
        elif "volume up" in query:
            pyautogui.press("volumeup")
            speak("Volume increased")

        elif "volume down" in query:
            pyautogui.press("volumedown")
            speak("Volume decreased")

        elif "mute" in query:
            pyautogui.press("volumemute")
            speak("Volume muted")

        # Open Apps
        elif any(app in query for app in [
            "open calculator",
            "open notepad",
            "open paint"
        ]):
            openApp(query, speak)

        # Close Apps
        elif any(app in query for app in [
            "close calculator",
            "close notepad",
            "close paint"
        ]):
            closeApp(query, speak)

        # Browsing
        elif any(br in query for br in [
            "open google",
            "open edge"
        ]):
            browsing(query, speak, command)

        # System Condition
        elif any(sys_c in query for sys_c in [
            "system condition",
            "condition of the system"
        ]):
            speak("Checking system condition")
            condition(speak)

        # AI Fallback
        else:

            speak("Thinking...")

            response = ask_llm(query)

            save_memory(query, response)

            speak(response)

            time.sleep(1)


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("\nShutting down Jarvis gracefully...")

    finally:
        sys.exit()