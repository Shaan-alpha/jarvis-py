import core.paths as paths


def test_memory_path_under_user_data():
    import core.memory.semantic_memory as sm
    assert str(paths.user_data_dir()) in sm.MEMORY_PATH


def test_document_paths_under_user_data():
    import core.memory.document_memory as dm
    base = str(paths.user_data_dir())
    assert base in dm.DOCS_PATH
    assert base in dm.INDEX_PATH
    assert base in dm.CHUNKS_PATH


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
