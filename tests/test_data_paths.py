import core.paths as paths


def test_facts_path_under_user_data(monkeypatch):
    import core.memory.facts as facts
    # The autouse fixture points FACTS_PATH at a temp dir; check the real default.
    monkeypatch.undo()
    assert str(paths.user_data_dir()) in facts.FACTS_PATH


def test_document_paths_under_user_data():
    import core.memory.document_memory as dm
    base = str(paths.user_data_dir())
    assert base in dm.DOCS_PATH
    assert base in dm.INDEX_PATH
    assert base in dm.CHUNKS_PATH
    assert base in dm.MANIFEST_PATH


def test_profile_path_under_user_data():
    import core.memory.profile_memory as pm
    assert str(paths.user_data_dir()) in pm.PROFILE_PATH


def test_tasks_file_under_user_data():
    import core.tasks.task_storage as ts
    assert str(paths.user_data_dir()) in ts.TASKS_FILE


def test_save_profile_creates_parent(monkeypatch, tmp_path):
    import core.memory.profile_memory as pm
    target = tmp_path / "data" / "profile" / "user_profile.json"
    monkeypatch.setattr(pm, "PROFILE_PATH", str(target))
    pm.save_profile({"name": "Test"})
    assert target.exists()
