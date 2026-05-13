import threading
import uuid

from datetime import datetime, timedelta

from core.speech.engine import (
    speak
)

from core.tasks.task_storage import (
    load_tasks,
    save_tasks
)

from core.utils.logger import (
    logger
)


class TaskManager:

    def __init__(self):

        self.running = False
        self.tasks = load_tasks()
        self._timers = {}
        self._lock = threading.Lock()

    def start(self):

        if self.running:

            return

        self.running = True

        self._restore_tasks()

    def add_reminder_in_minutes(self, minutes, message):

        trigger_time = (
            datetime.now() + timedelta(minutes=minutes)
        )

        task = {
            "id": uuid.uuid4().hex,
            "time": trigger_time.isoformat(),
            "message": message
        }

        with self._lock:

            self.tasks.append(task)

            save_tasks(self.tasks)

        delay = minutes * 60

        self._schedule(task, delay)

    def _schedule(self, task, delay_seconds):

        timer = threading.Timer(
            max(0.0, delay_seconds),
            self._fire,
            args=(task,)
        )

        timer.daemon = True

        timer.start()

        self._timers[task["id"]] = timer

    def _fire(self, task):

        try:

            speak(f"Reminder. {task['message']}")

        finally:

            with self._lock:

                self.tasks = [
                    t for t in self.tasks
                    if t["id"] != task["id"]
                ]

                save_tasks(self.tasks)

            self._timers.pop(task["id"], None)

    def _restore_tasks(self):

        now = datetime.now()

        survivors = []

        for task in self.tasks:

            if "id" not in task:

                task["id"] = uuid.uuid4().hex

            task_time = datetime.fromisoformat(task["time"])

            remaining = (task_time - now).total_seconds()

            if remaining <= 0:

                logger.info(
                    f"Skipping expired reminder: "
                    f"{task['message']}"
                )

                continue

            survivors.append(task)

            self._schedule(task, remaining)

        if len(survivors) != len(self.tasks):

            self.tasks = survivors

            save_tasks(self.tasks)

    def stop(self):

        self.running = False

        for timer in list(self._timers.values()):

            timer.cancel()

        self._timers.clear()
