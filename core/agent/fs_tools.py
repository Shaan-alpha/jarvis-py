import difflib
import os
import re
import shutil
import time

from pathlib import Path, PureWindowsPath

from core.paths import user_data_dir

from core.agent.known_folders import known_folders

from core.agent.registry import Reply, tool

from core.state.conversation import conversation

from core.text import (
    normalize,
    plural,
    spoken_filename
)

from core.utils.logger import logger

from send2trash import send2trash


SPOKEN_CHARS = 100

SHOWN_CHARS = 2000

SPOKEN_ITEMS = 5

SHOWN_ITEMS = 50


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

    stripped = name.strip()

    candidate = Path(stripped)

    if candidate.is_absolute() or candidate.drive:

        return None

    # Also reject Windows drive / UNC paths under the Windows convention on any
    # host: on POSIX a string like "C:\\x" parses as a plain relative filename
    # (no drive), so the native check above misses it. PureWindowsPath sees the
    # drive on every platform, keeping the guard correct cross-OS (CI is Linux).
    win = PureWindowsPath(stripped)

    if win.is_absolute() or win.drive:

        return None

    root = _workspace().resolve()

    resolved = (root / candidate).resolve()

    if resolved == root or root not in resolved.parents:

        return None

    return resolved


def _preview(text):
    """Verbatim if short; otherwise speak a short preview and show more.

    Mirrors read_clipboard so spoken output never reads a huge blob aloud.
    """

    if len(text) <= SPOKEN_CHARS:

        return text

    preview = text[:SPOKEN_CHARS].rstrip()

    return Reply(
        say=f"Your file has {len(text)} characters. It starts: {preview}…",
        show=text[:SHOWN_CHARS],
    )


def _listing(names, *, all_intro, some_intro):
    """A short spoken list; the HUD gets up to SHOWN_ITEMS, one per line."""

    if len(names) <= SPOKEN_ITEMS:

        return f"{all_intro} " + ", ".join(names) + "."

    return Reply(
        say=f"{some_intro.format(count=len(names))} " + ", ".join(names[:SPOKEN_ITEMS]) + ".",
        show=f"{all_intro}\n" + "\n".join(names[:SHOWN_ITEMS]),
    )


# Never walked: app data, dependency trees, VCS and system folders.
SKIP_DIRS = {
    "appdata", "node_modules", ".git", "venv", ".venv", "__pycache__",
    "$recycle.bin", "windows", "program files", "program files (x86)", "site-packages",
}

MAX_DEPTH = 6

MAX_ENTRIES = 20000

SEARCH_SECONDS = 3.0

MAX_RESULTS = 10

# Opening one of these would run a program; open_file refuses them.
BLOCKED_OPEN = {
    ".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".jse", ".wsf", ".msi",
    ".com", ".scr", ".lnk", ".hta", ".reg",
}

_ORDINALS = {
    "first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2,
    "fourth": 3, "fifth": 4, "last": -1, "it": 0, "that": 0, "this": 0,
}


def user_roots():
    """{name: Path} of every folder the file tools may touch."""

    return known_folders(workspace=_workspace())


def _startfile(path):

    os.startfile(path)


def _recent_dir():

    return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Recent"


def _search_roots(roots):
    """Unique roots, dropping any root that sits inside another."""

    unique = []

    for path in sorted(set(roots.values()), key=lambda p: len(p.parts)):

        if not any(root == path or root in path.parents for root in unique):

            unique.append(path)

    return unique


# Reparse tags for links (IO_REPARSE_TAG_MOUNT_POINT = junction, _SYMLINK).
# Other reparse points — OneDrive files-on-demand — are ordinary files to us.
_LINK_TAGS = {0xA0000003, 0xA000000C}

_HIDDEN_OR_SYSTEM = 0x2 | 0x4


def _skip_entry(entry):
    """Links could lead outside the allowed folders (a junction in Documents
    exposed files anywhere to find, move and delete); hidden/system items are
    Windows plumbing (desktop.ini, $RECYCLE.BIN, a hidden stash)."""

    if entry.name.startswith((".", "~$")):

        return True

    try:

        if entry.is_symlink():

            return True

        info = entry.stat(follow_symlinks=False)

    except OSError:

        return True

    if getattr(info, "st_reparse_tag", 0) in _LINK_TAGS:

        return True

    return bool(getattr(info, "st_file_attributes", 0) & _HIDDEN_OR_SYSTEM)


def _scan(folder):

    try:

        return list(os.scandir(folder))

    except OSError:

        return []


def _walk(roots, clock=time.monotonic):
    """Yield files under the roots, bounded by depth, count and time."""

    deadline = clock() + SEARCH_SECONDS

    seen = 0

    stack = [(root, 0) for root in _search_roots(roots)]

    while stack:

        folder, depth = stack.pop()

        for entry in _scan(folder):

            seen += 1

            if seen > MAX_ENTRIES or clock() > deadline:

                return

            if _skip_entry(entry):

                continue

            if not entry.is_dir(follow_symlinks=False):

                yield Path(entry.path)

            elif depth < MAX_DEPTH and entry.name.lower() not in SKIP_DIRS:

                stack.append((entry.path, depth + 1))


def _match_key(text):

    return normalize(spoken_filename(text)).replace("_", " ").replace("-", " ")


def _mtime(path):

    try:

        return path.stat().st_mtime

    except OSError:

        return 0


def find_paths(name, roots=None):
    """Files matching `name`: exact name/stem first, then names containing it
    (newest first), then close spellings. At most MAX_RESULTS."""

    roots = roots or user_roots()

    target = _match_key(name)

    if not target:

        return []

    exact, partial, others = [], [], {}

    for path in _walk(roots):

        key, stem = _match_key(path.name), _match_key(path.stem)

        if target in (key, stem):

            exact.append(path)

        elif target in key:

            partial.append(path)

        else:

            others.setdefault(stem, []).append(path)

    partial.sort(key=_mtime, reverse=True)

    found = exact + partial

    if not found:

        for stem in difflib.get_close_matches(target, list(others), n=MAX_RESULTS, cutoff=0.75):

            found.extend(others[stem])

    return found[:MAX_RESULTS]


def folder_label(path, roots):
    """'Downloads' — the deepest known folder holding `path`."""

    best = None

    for name, root in roots.items():

        if root == path.parent or root in path.parents:

            if best is None or len(root.parts) > len(roots[best].parts):

                best = name

    return best.capitalize() if best else str(path.parent)


def _numbered(paths):

    return "\n".join(f"{i}. {path}" for i, path in enumerate(paths, 1))


@tool(
    "find_file",
    "Find a file by name in your folders",
    params={"name": {"type": "str", "required": True, "desc": "the file name, e.g. report"}},
    llm=False,
)
def find_file(name):

    roots = user_roots()

    found = find_paths(name, roots)

    conversation.set_results([str(path) for path in found])

    if not found:

        return f"I couldn't find {name}."

    labels = [f"{path.name} in {folder_label(path, roots)}" for path in found]

    if len(found) == 1:

        say = f"Found {labels[0]}. Say 'open it' to open it."

    else:

        say = f"Found {len(found)}: " + ", ".join(labels[:3]) + ("." if len(found) <= 3 else ", and more.")

    return Reply(say=say, show=_numbered(found))


def _open_path(path):

    if path.suffix.lower() in BLOCKED_OPEN:

        return "I won't run programs from files. Say 'open' and the app name instead."

    if not path.exists():

        return f"{path.name} isn't there anymore."

    try:

        _startfile(str(path))

    except OSError:

        return f"I couldn't open {path.name}."

    return f"Opening {path.name}."


def _ordinal(name):

    key = re.sub(r"^the ", "", normalize(name))

    key = re.sub(r" (?:one|file|result)$", "", key)

    return _ORDINALS.get(key)


@tool(
    "open_file",
    "Open a file by name, or one of the files just found",
    params={"name": {"type": "str", "required": True, "desc": "a file name, or first/second/last/it"}},
    llm=False,
)
def open_file(name):

    # Opening a near match is harmless (nothing changes), so no confirmation.
    path, _exact, problem = _target(name, user_roots())

    if problem:

        return problem

    return _open_path(path)


@tool(
    "open_folder",
    "Open one of your folders (desktop, documents, downloads, ...)",
    params={"folder": {"type": "str", "required": True, "desc": "e.g. downloads"}},
    llm=False,
)
def open_folder(folder):

    key = normalize(folder).replace(" folder", "").strip()

    path = user_roots().get(key)

    if path is None:

        return f"I don't know a folder called {folder}."

    _startfile(str(path))

    return f"Opening {key.capitalize()}."


_BAD_NAME_CHARS = set('\\/:*?"<>|')


def _target(name, roots):
    """The file a command means, as (path, exact, problem).

    "it" / "the second one" pick from the files just found — never a search
    for a file literally named "it". Otherwise one exact name/stem match is
    exact; a single near match (substring or close spelling) comes back with
    exact=False so changes can confirm it first."""

    index = _ordinal(name)

    if index is not None:

        results = conversation.results()

        if not results:

            return None, False, "Which file? Say 'find' and its name first."

        if index >= len(results):

            return None, False, f"I only found {plural(len(results), 'file')}."

        return Path(results[index]), True, None

    found = find_paths(name, roots)

    target = _match_key(name)

    exact = [p for p in found if target in (_match_key(p.name), _match_key(p.stem))]

    choices = exact or found

    if not choices:

        return None, False, f"I couldn't find {name}."

    if len(choices) > 1:

        conversation.set_results([str(path) for path in choices])

        return None, False, Reply(
            say=f"I found {len(choices)} files called {name}. Say which one, like 'the first one'.",
            show=_numbered(choices),
        )

    return choices[0], bool(exact), None


def _confirm_near_match(name, path, verb, run):
    """Never move or rename a file the user didn't name exactly without a yes."""

    conversation.set_pending(f"{verb} {path}", run)

    return f"I couldn't find {name} exactly. Did you mean {path.name}? Say yes to {verb} it."


@tool(
    "move_file",
    "Move a file into one of your folders",
    params={
        "name": {"type": "str", "required": True, "desc": "the file to move"},
        "folder": {"type": "str", "required": True, "desc": "desktop, documents, downloads, ..."},
    },
    llm=False,
)
def move_file(name, folder):

    roots = user_roots()

    key = normalize(folder).replace(" folder", "").strip()

    destination = roots.get(key)

    if destination is None:

        return f"I don't know a folder called {folder}."

    source, exact, problem = _target(name, roots)

    if problem:

        return problem

    if not exact:

        return _confirm_near_match(name, source, "move", lambda: _move(source, destination, key))

    return _move(source, destination, key)


def _move(source, destination, label):

    target = destination / source.name

    if source.parent == destination:

        return f"{source.name} is already in {label.capitalize()}."

    if target.exists():

        return f"{source.name} already exists in {label.capitalize()}."

    shutil.move(str(source), str(target))

    return f"Moved {source.name} to {label.capitalize()}."


@tool(
    "rename_file",
    "Rename a file (keeps its extension unless you give one)",
    params={
        "name": {"type": "str", "required": True, "desc": "the file to rename"},
        "new_name": {"type": "str", "required": True, "desc": "the new name"},
    },
    llm=False,
)
def rename_file(name, new_name):

    new = spoken_filename(new_name or "").strip().strip(".")

    if not new or any(ch in _BAD_NAME_CHARS for ch in new) or ".." in new:

        return "That isn't a valid file name."

    source, exact, problem = _target(name, user_roots())

    if problem:

        return problem

    if not exact:

        return _confirm_near_match(name, source, "rename", lambda: _rename(source, new))

    return _rename(source, new)


def _rename(source, new):

    if not Path(new).suffix:

        new += source.suffix

    target = source.with_name(new)

    if target.exists():

        return f"{new} already exists there."

    source.rename(target)

    return f"Renamed {source.name} to {new}."


def _recycle(path):

    if not path.exists():

        return f"{path.name} is already gone."

    try:

        send2trash(str(path))

    except OSError:

        return f"I couldn't delete {path.name}."

    return f"Moved {path.name} to the Recycle Bin."


@tool(
    "delete_file",
    "Move a file to the Recycle Bin (asks for confirmation first)",
    params={"name": {"type": "str", "required": True, "desc": "the file to delete"}},
    llm=False,
)
def delete_file(name):

    roots = user_roots()

    # Always confirmed, and the prompt names the actual file — so a near match
    # is safe to offer here.
    source, _exact, problem = _target(name, roots)

    if problem:

        return problem

    if not source.is_file():

        return "I only delete files, not folders."

    conversation.set_pending(f"recycle {source}", lambda: _recycle(source))

    return f"Move {source.name} from {folder_label(source, roots)} to the Recycle Bin? Say yes to confirm."


@tool("recent_files", "List recently opened files", llm=False)
def recent_files():

    try:

        links = sorted(_recent_dir().glob("*.lnk"), key=_mtime, reverse=True)

    except OSError:

        links = []

    names = [link.stem for link in links[:10]]

    if not names:

        return "I can't see any recent files."

    return Reply(
        say="Recently opened: " + ", ".join(names[:5]) + ".",
        show="Recent files:\n" + "\n".join(names),
    )


@tool("list_files", "List the files in your Jarvis workspace folder")
def list_files():

    names = sorted(p.name for p in _workspace().iterdir() if p.is_file())

    if not names:

        return "Your workspace is empty."

    return _listing(
        names,
        all_intro="Your workspace has:",
        some_intro="Your workspace has {count} files, including",
    )


@tool(
    "read_file",
    "Read a text file from your Jarvis workspace folder",
    params={
        "name": {
            "type": "str",
            "required": True,
            "desc": "the file to read, e.g. notes.txt",
        }
    },
)
def read_file(name):

    path = _resolve_in_workspace(name)

    if path is None:

        return "That path is outside my workspace."

    if not path.is_file():

        return f"I couldn't find {name} in your workspace."

    try:

        text = path.read_text(encoding="utf-8")

    except (OSError, UnicodeDecodeError) as e:

        logger.warning(f"read_file failed for {name!r}: {e}")

        return f"I couldn't read {name}."

    if not text.strip():

        return f"{name} is empty."

    return _preview(text)


@tool(
    "write_file",
    "Save text to a new file in your Jarvis workspace folder",
    params={
        "name": {
            "type": "str",
            "required": True,
            "desc": "the file name to save, e.g. notes.txt",
        },
        "content": {
            "type": "str",
            "required": True,
            "desc": "the text to write into the file",
        },
    },
)
def write_file(name, content):

    path = _resolve_in_workspace(name)

    if path is None:

        return "That path is outside my workspace."

    if path.exists():

        return f"{name} already exists; pick another name."

    try:

        path.write_text(content, encoding="utf-8")

    except OSError as e:

        logger.warning(f"write_file failed for {name!r}: {e}")

        return f"I couldn't save {name}."

    return f"Saved {name}."


@tool(
    "search_files",
    "Find files in your Jarvis workspace whose name matches a query",
    params={
        "query": {
            "type": "str",
            "required": True,
            "desc": "text to match against file names",
        }
    },
)
def search_files(query):

    q = query.strip().lower()

    matches = sorted(
        p.name for p in _workspace().iterdir()
        if p.is_file() and q in p.name.lower()
    )

    if not matches:

        return f"No files match {query}."

    return _listing(
        matches,
        all_intro="Matches:",
        some_intro="{count} files match, including",
    )
