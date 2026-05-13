import os
import webbrowser

import pyautogui

from core.utils.logger import (
    logger
)


def execute_tool(tool):

    try:

        if tool == "open_calculator":

            os.startfile(
                r"C:\Windows\System32\calc.exe"
            )

            return "Opening calculator."

        elif tool == "open_youtube":

            webbrowser.open(
                "https://youtube.com"
            )

            return "Opening YouTube."

        elif tool == "open_google":

            webbrowser.open(
                "https://google.com"
            )

            return "Opening Google."

        elif tool == "increase_volume":

            for _ in range(5):

                pyautogui.press("volumeup")

            return "Increasing volume."

        elif tool == "decrease_volume":

            for _ in range(5):

                pyautogui.press("volumedown")

            return "Decreasing volume."

        elif tool == "mute_volume":

            pyautogui.press("volumemute")

            return "Volume muted."

        return None

    except Exception as e:

        logger.exception(
            f"Tool Execution Error: {e}"
        )

        return "Tool execution failed."
