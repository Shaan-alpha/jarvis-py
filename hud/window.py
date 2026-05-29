# hud/window.py
import os

# pyrefly: ignore [missing-import]
import webview

from config.settings import (
    HUD_WS_HOST,
    HUD_WS_PORT,
)


def _web_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "web", "index.html")


def launch():
    ws_url = f"ws://{HUD_WS_HOST}:{HUD_WS_PORT}"

    url = f"file:///{_web_path().replace(os.sep, '/')}?ws={ws_url}"

    webview.create_window(
        "Jarvis",
        url=url,
        width=380,
        height=240,
        x=40,
        y=40,
        frameless=True,
        easy_drag=True,
        on_top=True,
        resizable=False,
        background_color="#05080f",
    )

    webview.start()
