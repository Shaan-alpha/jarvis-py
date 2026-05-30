import json
import os

from core.paths import user_data_dir


TASKS_FILE = os.path.join(
    str(user_data_dir()),
    "data",
    "tasks",
    "tasks.json"
)


def load_tasks():

    if not os.path.exists(
        TASKS_FILE
    ):

        return []

    with open(
        TASKS_FILE,
        "r"
    ) as file:

        return json.load(file)


def save_tasks(tasks):

    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)

    with open(
        TASKS_FILE,
        "w"
    ) as file:

        json.dump(
            tasks,
            file,
            indent=4
        )
