import importlib.util

from core.paths import (
    resource_dir,
    user_data_dir,
)

from core.utils.logger import (
    logger
)


def _plugin_dirs():

    return [
        resource_dir() / "plugins",
        user_data_dir() / "plugins",
    ]


def _import_file(path):

    """Import a plugin file for its side effects (tool registration).

    The module is intentionally NOT inserted into sys.modules, so importing
    the same file again re-executes it and re-runs its @tool decorators.
    """

    spec = importlib.util.spec_from_file_location(path.stem, str(path))

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)


def load_builtins():

    import sys

    # Remove from sys.modules so re-import always re-executes @tool decorators.
    sys.modules.pop("core.agent.builtins", None)

    import core.agent.builtins  # noqa: F401  (decorators register on import)


def load_plugins(dirs):

    seen = set()

    for d in dirs:

        resolved = d.resolve()

        if resolved in seen or not d.exists():

            continue

        seen.add(resolved)

        for path in sorted(d.glob("*.py")):

            if path.name.startswith("_"):

                continue

            try:

                _import_file(path)

            except Exception as e:

                logger.exception(f"Skipping bad plugin {path}: {e}")


def init_tools():

    load_builtins()

    load_plugins(_plugin_dirs())
