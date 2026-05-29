import time

from core.state.session_manager import SessionManager


def test_starts_inactive():
    session = SessionManager(timeout=20)
    assert session.active is False


def test_activate_and_deactivate():
    session = SessionManager(timeout=20)
    session.activate()
    assert session.active is True
    session.deactivate()
    assert session.active is False


def test_not_expired_immediately():
    session = SessionManager(timeout=20)
    session.activate()
    assert session.is_expired() is False


def test_expires_after_timeout():
    session = SessionManager(timeout=0)
    session.activate()
    time.sleep(0.01)
    assert session.is_expired() is True


def test_update_interaction_resets_timer():
    session = SessionManager(timeout=1)
    session.activate()
    session.update_interaction()
    assert session.is_expired() is False
