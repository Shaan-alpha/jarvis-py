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
    usage = str(psutil.cpu_percent())
    speak_func(f"CPU is at {usage} percentage")
    battery = psutil.sensors_battery()
    percentage = battery.percent
    speak_func(f"Boss our system have {percentage} percentage battery")

    if percentage >= 80:
        speak_func("Boss we could have enough charging to continue our recording")
    elif percentage >= 40 and percentage <= 75:
        speak_func("Boss we should connect our system to charging point to charge our battery")
    else:
        speak_func("Boss we have very low power, please connect to charging otherwise recording should be off...")
