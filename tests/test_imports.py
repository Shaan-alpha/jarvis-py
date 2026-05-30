import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))


def test_core_imports():
    """Verify that core utility modules can be imported."""
    from core.utils import logger
    assert logger is not None


def test_logger_log_dir_under_user_data(monkeypatch):
    import core.paths as paths
    import core.utils.logger as lg
    assert str(paths.user_data_dir()) in lg.LOG_DIR
