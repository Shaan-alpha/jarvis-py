import webbrowser
from core.utils.helpers import cal_day

def social_media(command_text, speak_func):
    if 'facebook' in command_text:
        speak_func("opening your facebook")
        webbrowser.open("https://www.facebook.com/")
    elif 'whatsapp' in command_text:
        speak_func("opening your whatsapp")
        webbrowser.open("https://web.whatsapp.com/")
    elif 'discord' in command_text:
        speak_func("opening your discord server")
        webbrowser.open("https://discord.com/")
    elif 'instagram' in command_text:
        speak_func("opening your instagram")
        webbrowser.open("https://www.instagram.com/")
    elif 'youtube' in command_text:
        speak_func("opening your youtube channel")
        webbrowser.open("https://www.youtube.com/")
    else:
        speak_func("No result found")

def schedule(speak_func):
    day = cal_day().lower()
    speak_func("Boss today's schedule is ")
    week = {
        "monday": "Boss, from 9:00 to 9:50 you have Algorithms class, from 10:00 to 11:50 you have System Design class, from 12:00 to 2:00 you have a break, and today you have Programming Lab from 2:00 onwards.",
        "tuesday": "Boss, from 9:00 to 9:50 you have Web Development class, from 10:00 to 10:50 you have a break, from 11:00 to 12:50 you have Database Systems class, from 1:00 to 2:00 you have a break, and today you have Open Source Projects lab from 2:00 onwards.",
        "wednesday": "Boss, today you have a full day of classes. From 9:00 to 10:50 you have Machine Learning class, from 11:00 to 11:50 you have Operating Systems class, from 12:00 to 12:50 you have Ethics in Technology class, from 1:00 to 2:00 you have a break, and today you have Software Engineering workshop from 2:00 onwards.",
        "thursday": "Boss, today you have a full day of classes. From 9:00 to 10:50 you have Computer Networks class, from 11:00 to 12:50 you have Cloud Computing class, from 1:00 to 2:00 you have a break, and today you have Cybersecurity lab from 2:00 onwards.",
        "friday": "Boss, today you have a full day of classes. From 9:00 to 9:50 you have Artificial Intelligence class, from 10:00 to 10:50 you have Advanced Programming class, from 11:00 to 12:50 you have UI/UX Design class, from 1:00 to 2:00 you have a break, and today you have Capstone Project work from 2:00 onwards.",
        "saturday": "Boss, today you have a more relaxed day. From 9:00 to 11:50 you have team meetings for your Capstone Project, from 12:00 to 12:50 you have Innovation and Entrepreneurship class, from 1:00 to 2:00 you have a break, and today you have extra time to work on personal development and coding practice from 2:00 onwards.",
        "sunday": "Boss, today is a holiday, but keep an eye on upcoming deadlines and use this time to catch up on any reading or project work."
    }
    if day in week.keys():
        speak_func(week[day])

def browsing(query, speak_func, command_func):
    if 'google' in query:
        speak_func("Boss, what should i search on google..")
        s = command_func().lower()
        webbrowser.open(f"{s}")
