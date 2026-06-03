from pathlib import Path

from core.paths import user_data_dir

from core.agent.registry import tool

from core.utils.logger import logger


FILE_PREVIEW_LIMIT = 200

FILE_LIST_LIMIT = 20


def _workspace():

    root = user_data_dir() / "workspace"

    root.mkdir(parents=True, exist_ok=True)

    return root


def _resolve_in_workspace(name):
    """Resolve a user-supplied name inside the workspace, or None if it escapes.

    Rejects empty input, absolute paths / drive letters, and any path whose
    resolved real location is not strictly inside the workspace root (blocks
    ../ traversal and the root itself). Returns the safe absolute Path, or None.
    """

    if not name or not name.strip():

        return None

    candidate = Path(name.strip())

    if candidate.is_absolute() or candidate.drive:

        return None

    root = _workspace().resolve()

    resolved = (root / candidate).resolve()

    if resolved == root or root not in resolved.parents:

        return None

    return resolved


def _preview(text):
    """Verbatim if short; otherwise a length report + truncated preview.

    Mirrors read_clipboard so spoken output never reads a huge blob aloud.
    """

    if len(text) <= FILE_PREVIEW_LIMIT:

        return text

    return (
        f"Your file has {len(text)} characters. "
        f'It starts: "{text[:FILE_PREVIEW_LIMIT]}..." (truncated).'
    )


@tool("list_files", "List the files in your Jarvis workspace folder")
def list_files():

    names = sorted(p.name for p in _workspace().iterdir() if p.is_file())

    if not names:

        return "Your workspace is empty."

    if len(names) <= FILE_LIST_LIMIT:

        return "Your workspace has: " + ", ".join(names) + "."

    shown = ", ".join(names[:FILE_LIST_LIMIT])

    return f"Your workspace has {len(names)} files, including: {shown}."
