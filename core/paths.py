import os
import sys

from pathlib import Path


def is_frozen():
    """True when running inside a PyInstaller bundle."""

    return getattr(sys, "frozen", False)


def resource_dir():
    """Base dir for read-only bundled assets (models, hud/web).

    Frozen: ``sys._MEIPASS`` — for a PyInstaller one-folder build this is the
    ``_internal/`` folder where bundled ``datas`` land (PyInstaller >= 6 moves
    everything except the executable there), so it is NOT the same as the
    executable's folder. Falls back to the exe folder if ``_MEIPASS`` is absent.
    Source: the repo root (parent of the core/ package).
    """

    if is_frozen():

        meipass = getattr(sys, "_MEIPASS", None)

        if meipass:

            return Path(meipass)

        return Path(sys.executable).parent

    return Path(__file__).resolve().parent.parent


def user_data_dir():
    """Base dir for writable user data (profile, memory, tasks, logs).

    Frozen: %APPDATA%\\JarvisAI.  Source: the repo root (so dev is
    unchanged). The directory is created if it does not yet exist.
    """

    if is_frozen():

        appdata = os.environ.get("APPDATA")

        if not appdata:

            raise RuntimeError(
                "APPDATA environment variable is not set; "
                "cannot locate the user data directory."
            )

        base = Path(appdata) / "JarvisAI"

    else:

        base = Path(__file__).resolve().parent.parent

    base.mkdir(parents=True, exist_ok=True)

    return base
