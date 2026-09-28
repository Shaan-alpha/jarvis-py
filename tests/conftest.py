import copy

import pytest

from core.agent import registry
from core.agent import loader
from core.ai import llm_health
from core import net
from core.state.conversation import conversation
from core.memory import facts as facts_store


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


@pytest.fixture(autouse=True)
def _no_real_network_probes(monkeypatch):
    # Unit tests never touch the network: every connectivity probe reads
    # "offline" unless a test overrides net._probe itself.
    monkeypatch.setattr(net, "_probe", lambda host, port, timeout: False)
    net.reset_cache()
    yield
    net.reset_cache()


@pytest.fixture(autouse=True)
def _fresh_conversation():
    conversation.clear()
    yield
    conversation.clear()


@pytest.fixture(autouse=True)
def _isolated_facts(tmp_path, monkeypatch):
    monkeypatch.setattr(facts_store, "FACTS_PATH", str(tmp_path / "facts.json"))
    facts_store.reset_cache()
    yield
    facts_store.reset_cache()
