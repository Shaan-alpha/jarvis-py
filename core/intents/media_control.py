def handle_media_control(query, speak):

    # Imported lazily: pyautogui needs a DISPLAY at import time, which
    # breaks importing this module on headless CI. Only loaded when a
    # media command actually runs.
    import pyautogui

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
