import json

from datetime import datetime, timedelta

import core.tasks.task_manager as tm
import core.tasks.task_storage as ts


def _write_tasks(path, rows):
    path.write_text(json.dumps(rows), encoding="utf-8")


def test_start_skips_unparseable_reminders(tmp_path, monkeypatch):
    # tasks.json is restored at startup, before the mic check — so one unreadable
    # row (a truncated write, a hand-edit, an older schema) used to raise straight
    # out of TaskManager.start() and Jarvis wouldn't boot at all. Bad rows are
    # dropped; the good ones still get scheduled.
    path = tmp_path / "tasks.json"

    future = (datetime.now() + timedelta(hours=1)).isoformat()

    _write_tasks(path, [
        {"id": "bad-time", "time": "not-a-timestamp", "message": "corrupt"},
        {"id": "no-time", "message": "missing the time field"},
        {"id": "good", "time": future, "message": "keep me"},
    ])

    monkeypatch.setattr(ts, "TASKS_FILE", str(path))

    manager = tm.TaskManager()

    manager.start()

    try:

        assert [task["id"] for task in manager.tasks] == ["good"]

    finally:

        manager.stop()


def test_start_rewrites_the_file_without_the_bad_rows(tmp_path, monkeypatch):
    path = tmp_path / "tasks.json"

    _write_tasks(path, [{"id": "bad", "time": "nonsense", "message": "corrupt"}])

    monkeypatch.setattr(ts, "TASKS_FILE", str(path))

    manager = tm.TaskManager()

    manager.start()

    manager.stop()

    assert json.loads(path.read_text(encoding="utf-8")) == []
