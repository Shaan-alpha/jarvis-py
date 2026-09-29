# hud/window.py
import ctypes
import os
import sys
import time

# pyrefly: ignore [missing-import]
import webview

from config.settings import (
    HUD_BACKGROUND,
    HUD_BORDER_RGB,
    HUD_HEIGHT,
    HUD_WIDTH,
    HUD_WS_HOST,
    HUD_WS_PORT,
)

from core.hud.theming import theme_for_hour


class _Api:
    """Window controls exposed to the HUD JS as ``window.pywebview.api.*``.

    The close button drives a full shutdown: the page first sends a ``shutdown``
    command over the WebSocket (which stops the backend's voice loop / TTS / WS
    threads), then calls ``quit()`` here to destroy this window — returning from
    ``webview.start()`` so the HUD process exits too. Nothing is left running.

    The window handle is ``_window``, and the underscore is load-bearing:
    pywebview builds the JS bridge by walking every public attribute of this
    object and recursing into nested ones (``webview.util.get_functions`` skips
    underscore-prefixed names). Held publicly, the walk reached the native
    WinForms object and recursed through ``window.native.AccessibilityObject
    .Bounds.Empty.Empty…`` — each .NET property returning a fresh wrapper, so
    pywebview's id()-based cycle guard never tripped — until the stack blew.
    That froze the GUI thread ("Not Responding") and killed the HUD process.
    """

    def __init__(self):
        self._window = None

    def minimize(self):
        if self._window:
            self._window.minimize()

    def quit(self):
        if self._window:
            self._window.destroy()


def _web_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "web", "index.html")


# Windows 11 DWM window attributes (dwmapi.h).
_DWMWA_WINDOW_CORNER_PREFERENCE = 33

_DWMWCP_ROUND = 2

_DWMWA_BORDER_COLOR = 34


def _colorref(rgb):
    red, green, blue = rgb
    return red | (green << 8) | (blue << 16)


def apply_native_frame(hwnd, dwm=None):
    """Round the frameless window's corners and give it a 1px native outline.

    pywebview can't make a window transparent on Windows, so a CSS-rounded panel
    left dark square corners. DWM rounds the real window instead. Returns True
    when DWM accepted both attributes; False (nothing changes) on Windows 10,
    other OSes or any failure."""
    try:
        dwm = dwm or ctypes.windll.dwmapi
        corner = ctypes.c_int(_DWMWCP_ROUND)
        border = ctypes.c_uint(_colorref(HUD_BORDER_RGB))
        rounded = dwm.DwmSetWindowAttribute(
            hwnd, _DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(corner), ctypes.sizeof(corner)
        )
        outlined = dwm.DwmSetWindowAttribute(
            hwnd, _DWMWA_BORDER_COLOR, ctypes.byref(border), ctypes.sizeof(border)
        )
        return rounded == 0 and outlined == 0
    except (AttributeError, OSError, ValueError):
        return False


def _on_shown(window):
    """Apply the native frame once the window exists. pywebview passes the
    window because the parameter is named ``window``. The native handle is only
    touched here — never stored on _Api (see its docstring)."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(window.native.Handle.ToInt64())
    except Exception:
        return
    apply_native_frame(hwnd)


def launch():
    ws_url = f"ws://{HUD_WS_HOST}:{HUD_WS_PORT}"

    theme = theme_for_hour(time.localtime().tm_hour)

    # Fragment (#), not query (?): file:// treats a query as part of the file
    # name. The theme rides along so the first paint is already the right one.
    url = f"file:///{_web_path().replace(os.sep, '/')}#ws={ws_url}&theme={theme}"

    api = _Api()

    window = webview.create_window(
        "Jarvis",
        url=url,
        js_api=api,
        width=HUD_WIDTH,
        height=HUD_HEIGHT,
        x=40,
        y=40,
        frameless=True,
        # Drag only from the title bar (pywebview-drag-region in index.html), so
        # reply text can be selected and copied.
        easy_drag=False,
        text_select=True,
        on_top=True,
        resizable=False,
        background_color=HUD_BACKGROUND,
    )

    api._window = window

    window.events.shown += _on_shown

    # Blocking GUI loop. pywebview requires this to run on the main thread, so
    # the caller (app.main when frozen) puts the voice loop on a background
    # thread and calls launch() on the main thread. Closing the window returns
    # from here and the process exits.
    webview.start()
