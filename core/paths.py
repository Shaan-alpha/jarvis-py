import os
import sys

from pathlib import Path


def is_frozen():
    """True when running inside a PyInstaller bundle."""

    return getattr(sys, "frozen", False)
