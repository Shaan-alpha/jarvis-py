import pyautogui


def handle_media_control(query, speak):

    if "volume up" in query:
        pyautogui.press("volumeup")
        speak("Volume increased")

    elif "volume down" in query:
        pyautogui.press("volumedown")
        speak("Volume decreased")

    elif "mute" in query:
        pyautogui.press("volumemute")
        speak("Volume muted")