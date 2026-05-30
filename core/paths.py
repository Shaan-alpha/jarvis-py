import os
import sys

from pathlib import Path


def is_frozen():
    """True when running inside a PyInstaller bundle."""

    return getattr(sys, "frozen", False)


def resource_dir():
    """Base dir for read-only bundled assets (models, hud/web).

    Frozen (one-folder): the folder containing the executable.
    Source: the repo root (parent of the core/ package).
    """

    if is_frozen():

        return Path(sys.executable).parent

    return Path(__file__).resolve().parent.parent
