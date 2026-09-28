import copy

import pytest

from core.agent import registry
from core.agent import loader
from core.ai import llm_health


@pytest.fixture(autouse=True)
def _isolate_registry():
    loader.load_builtins()
    snapshot = copy.deepcopy(registry._REGISTRY)
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(snapshot)


@pytest.fixture(autouse=True)
def _reset_llm_health():
    llm_health.mark_up()
    yield
    llm_health.mark_up()
