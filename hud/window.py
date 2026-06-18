# hud/window.py
import os

# pyrefly: ignore [missing-import]
import webview

from config.settings import (
    HUD_WS_HOST,
    HUD_WS_PORT,
)


class _Api:
    """Window controls exposed to the HUD JS as ``window.pywebview.api.*``.

    The close button drives a full shutdown: the page first sends a ``shutdown``
    command over the WebSocket (which stops the backend's voice loop / TTS / WS
    threads), then calls ``quit()`` here to destroy this window — returning from
    ``webview.start()`` so the HUD process exits too. Nothing is left running.
    """

    def __init__(self):
        self.window = None

    def minimize(self):
        if self.window:
            self.window.minimize()

    def quit(self):
        if self.window:
            self.window.destroy()


def _web_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "web", "index.html")


def launch():
    ws_url = f"ws://{HUD_WS_HOST}:{HUD_WS_PORT}"

    # Pass the WS URL as a fragment (#), not a query (?): the file:// scheme
    # treats a query string as part of the filename (-> "File not found"),
    # whereas a fragment is never part of the path and is still readable via
    # location.hash in the page.
    url = f"file:///{_web_path().replace(os.sep, '/')}#ws={ws_url}"

    api = _Api()

    window = webview.create_window(
        "Jarvis",
        url=url,
        js_api=api,
        width=440,
        height=410,
        x=40,
        y=40,
        frameless=True,
        easy_drag=True,
        on_top=True,
        resizable=False,
        background_color="#05080f",
    )

    api.window = window

    # Blocking GUI loop. pywebview requires this to run on the main thread, so
    # the caller (app.main when frozen) puts the voice loop on a background
    # thread and calls launch() on the main thread. Closing the window returns
    # from here and the process exits.
    webview.start()
