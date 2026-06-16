import os

from core.paths import user_data_dir

from core.utils.jsonio import (
    read_json,
    write_json_atomic,
)


TASKS_FILE = os.path.join(
    str(user_data_dir()),
    "data",
    "tasks",
    "tasks.json"
)


def load_tasks():

    return read_json(TASKS_FILE, default=[])


def save_tasks(tasks):

    write_json_atomic(TASKS_FILE, tasks)
