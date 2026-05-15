import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))


def test_core_imports():
    """Verify that core utility modules can be imported."""
    from core.utils import logger
    assert logger is not None
