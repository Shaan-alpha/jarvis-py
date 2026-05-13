import datetime
import time

from core.memory.profile_memory import (
    load_profile
)


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


def _user_name():
    profile = load_profile()
    name = profile.get("name", "Boss")
    return name.split()[0] if name else "Boss"


def wishMe(speak_func):
    hour = int(datetime.datetime.now().hour)
    t = time.strftime("%I:%M:%p")
    day = cal_day()
    name = _user_name()

    if (hour >= 0) and (hour <= 12) and ('AM' in t):
        speak_func(f"Good morning {name}, it's {day} and the time is {t}")
    elif (hour >= 12) and (hour <= 16) and ('PM' in t):
        speak_func(f"Good afternoon {name}, it's {day} and the time is {t}")
    else:
        speak_func(f"Good evening {name}, it's {day} and the time is {t}")
