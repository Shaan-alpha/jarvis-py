import datetime
import time

def cal_day():
    day = datetime.datetime.today().weekday() + 1
    day_dict = {
        1: "Monday",
        2: "Tuesday",
        3: "Wednesday",
        4: "Thursday",
        5: "Friday",
        6: "Saturday",
        7: "Sunday"
    }
    return day_dict.get(day, "None")

def wishMe(speak_func):
    hour = int(datetime.datetime.now().hour)
    t = time.strftime("%I:%M:%p")
    day = cal_day()

    if (hour >= 0) and (hour <= 12) and ('AM' in t):
        speak_func(f"Good morning Shaan, it's {day} and the time is {t}")
    elif (hour >= 12) and (hour <= 16) and ('PM' in t):
        speak_func(f"Good afternoon Shaan, it's {day} and the time is {t}")
    else:
        speak_func(f"Good evening Shaan, it's {day} and the time is {t}")
