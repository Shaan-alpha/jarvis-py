"""The user's real folders — Desktop, Documents, Downloads, Pictures, Music,
Videos — resolved through Windows Known Folders, so a OneDrive-redirected
Documents is found where it actually lives. Elsewhere: ~/<Name>."""

import ctypes
import os
import sys
import uuid

from pathlib import Path


# FOLDERID_* GUIDs (KnownFolders.h).
_FOLDER_IDS = {
    "desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
    "downloads": "374DE290-123F-4565-9164-39C4925E467B",
    "pictures": "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "music": "4BD8D571-6D19-48D3-BE97-422220080E43",
    "videos": "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
}


class _GUID(ctypes.Structure):

    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(text):

    value = uuid.UUID(text)

    return _GUID(
        value.time_low,
        value.time_mid,
        value.time_hi_version,
        (ctypes.c_ubyte * 8)(*value.bytes[8:]),
    )


def _shell_folder(folder_id):
    """SHGetKnownFolderPath; None when the call fails."""

    path = ctypes.c_wchar_p()

    guid = _guid(folder_id)

    result = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(guid), 0, None, ctypes.byref(path)
    )

    try:

        return path.value if result == 0 else None

    finally:

        ctypes.windll.ole32.CoTaskMemFree(path)


def _default_resolver(name, folder_id):

    if sys.platform == "win32":

        try:

            found = _shell_folder(folder_id)

            if found:

                return found

        except (OSError, AttributeError, ValueError):

            pass

    return str(Path.home() / name.capitalize())


def known_folders(workspace, resolver=None):
    """{name: Path} for each user folder that exists, plus the workspace."""

    resolver = resolver or _default_resolver

    folders = {}

    for name, folder_id in _FOLDER_IDS.items():

        raw = resolver(name, folder_id)

        if raw and os.path.isdir(raw):

            folders[name] = Path(raw).resolve()

    folders["workspace"] = Path(workspace).resolve()

    return folders
