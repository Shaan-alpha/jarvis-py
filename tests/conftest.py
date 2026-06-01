import copy

import pytest

from core.agent import registry
from core.agent import loader


@pytest.fixture(autouse=True)
def _isolate_registry():
    loader.load_builtins()
    snapshot = copy.deepcopy(registry._REGISTRY)
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(snapshot)
