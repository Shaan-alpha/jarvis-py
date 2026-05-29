import urllib.parse
import webbrowser


def browsing(query, speak_func, command_func):
    if 'google' in query:
        speak_func("Boss, what should I search on Google?")
        search_term = command_func()

        if not search_term or search_term == "none":
            speak_func("I didn't catch that. Try again.")
            return

        url = (
            "https://www.google.com/search?q="
            + urllib.parse.quote_plus(search_term)
        )

        speak_func(f"Searching Google for {search_term}")
        webbrowser.open(url)
