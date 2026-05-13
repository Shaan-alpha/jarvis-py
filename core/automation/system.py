import os

import psutil


def openApp(command_text, speak_func):
    if "calculator" in command_text:
        speak_func("opening calculator")
        os.startfile('C:\\Windows\\System32\\calc.exe')
    elif "notepad" in command_text:
        speak_func("opening notepad")
        os.startfile('C:\\Windows\\System32\\notepad.exe')
    elif "paint" in command_text:
        speak_func("opening paint")
        os.startfile('C:\\Windows\\System32\\mspaint.exe')


def closeApp(command_text, speak_func):
    if "calculator" in command_text:
        speak_func("closing calculator")
        os.system("taskkill /f /im calc.exe")
    elif "notepad" in command_text:
        speak_func("closing notepad")
        os.system('taskkill /f /im notepad.exe')
    elif "paint" in command_text:
        speak_func("closing paint")
        os.system('taskkill /f /im mspaint.exe')


def condition(speak_func):
    cpu = psutil.cpu_percent(interval=0.3)
    battery = psutil.sensors_battery()

    if battery is None:
        speak_func(f"CPU at {cpu:.0f} percent.")
        return

    pct = battery.percent
    charging = "charging" if battery.power_plugged else "on battery"
    speak_func(
        f"CPU at {cpu:.0f} percent, "
        f"battery {pct:.0f} percent, {charging}."
    )
