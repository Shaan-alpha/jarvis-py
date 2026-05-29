import pyautogui


def handle_media_control(query, speak):

    # Volume Up
    if any(word in query for word in [
        "volume up",
        "increase volume",
        "increase the volume",
        "raise volume",
        "raise the volume",
    ]):

        pyautogui.press("volumeup")

        speak("Volume increased")

    # Volume Down
    elif any(word in query for word in [
        "volume down",
        "decrease volume",
        "decrease the volume",
        "lower volume",
    ]):

        pyautogui.press("volumedown")

        speak("Volume decreased")

    # Mute
    elif any(word in query for word in [
        "mute",
        "mute volume",
        "volume mute",
    ]):

        pyautogui.press("volumemute")

        speak("Volume muted")
