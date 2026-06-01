import copy
import pytest

from core.agent import registry

try:
    from core.agent import loader
except ImportError:
    loader = None


@pytest.fixture(autouse=True)
def _isolate_registry():
    if loader is not None:
        loader.load_builtins()
    snapshot = copy.deepcopy(registry._REGISTRY)
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(snapshot)
