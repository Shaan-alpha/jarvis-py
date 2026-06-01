from core.agent import loader
from core.agent import registry


def test_load_plugins_registers(tmp_path):
    registry.clear()
    (tmp_path / "myplug.py").write_text(
        "from core.agent.registry import tool\n"
        "@tool('hello', 'say hi')\n"
        "def hello():\n"
        "    return 'hi'\n"
    )
    loader.load_plugins([tmp_path])
    spec = registry.get("hello")
    assert spec is not None
    assert spec.handler() == "hi"


def test_broken_plugin_is_skipped(tmp_path):
    (tmp_path / "bad.py").write_text("raise RuntimeError('boom')\n")
    # Must not raise.
    loader.load_plugins([tmp_path])


def test_missing_dir_is_skipped(tmp_path):
    # Must not raise.
    loader.load_plugins([tmp_path / "does_not_exist"])


def test_underscore_files_ignored(tmp_path):
    registry.clear()
    (tmp_path / "_helper.py").write_text(
        "from core.agent.registry import tool\n"
        "@tool('should_not_load', 'x')\n"
        "def f():\n"
        "    return None\n"
    )
    loader.load_plugins([tmp_path])
    assert registry.get("should_not_load") is None


def test_duplicate_dirs_loaded_once(tmp_path):
    (tmp_path / "p.py").write_text(
        "from core.agent.registry import tool\n"
        "@tool('once', 'x')\n"
        "def f():\n"
        "    return None\n"
    )
    # Passing the same dir twice must not double-import / error.
    loader.load_plugins([tmp_path, tmp_path])
    assert registry.get("once") is not None


def test_init_tools_loads_builtins():
    loader.init_tools()
    assert registry.get("open_app") is not None
