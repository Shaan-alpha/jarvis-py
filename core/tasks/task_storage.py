import json
import os


TASKS_FILE = (
    "data/tasks/tasks.json"
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

    with open(
        TASKS_FILE,
        "w"
    ) as file:

        json.dump(
            tasks,
            file,
            indent=4
        )