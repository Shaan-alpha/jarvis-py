import time
import threading
# pyrefly: ignore [missing-import]
import schedule
from datetime import datetime, timedelta

from core.speech.engine import (
    speak
)

from core.tasks.task_storage import (
    load_tasks,
    save_tasks
)


class TaskManager:

    def __init__(self):

        self.running = False

        self.tasks = load_tasks()

        self.restore_tasks()

    # -------------------- #
    # REMINDER ACTION
    # -------------------- #

    def reminder_job(
        self,
        message
    ):

        speak(
            f"Reminder. {message}"
        )

    # -------------------- #
    # ADD REMINDER
    # -------------------- #

    def add_reminder_in_minutes(
        self,
        minutes,
        message
    ):

        trigger_time = (
            datetime.now()
            + timedelta(minutes=minutes)
        )

        task = {
            "time": trigger_time.isoformat(),
            "message": message
        }

        self.tasks.append(task)

        save_tasks(self.tasks)

        schedule.every(
            minutes
        ).minutes.do(
            self.execute_task,
            task
        )

    # -------------------- #
    # EXECUTE TASK
    # -------------------- #

    def execute_task(
        self,
        task
    ):

        self.reminder_job(
            task["message"]
        )

        self.tasks.remove(task)

        save_tasks(self.tasks)

        return schedule.CancelJob

    # -------------------- #
    # RESTORE TASKS
    # -------------------- #

    def restore_tasks(self):

        now = datetime.now()

        for task in self.tasks:

            task_time = datetime.fromisoformat(
                task["time"]
            )

            remaining = (
                task_time - now
            ).total_seconds()

            if remaining > 0:

                minutes = max(
                    1,
                    int(remaining / 60)
                )

                schedule.every(
                    minutes
                ).minutes.do(
                    self.execute_task,
                    task
                )

    # -------------------- #
    # START LOOP
    # -------------------- #

    def start(self):

        if self.running:

            return

        self.running = True

        threading.Thread(
            target=self.run_scheduler,
            daemon=True
        ).start()

    # -------------------- #
    # SCHEDULER LOOP
    # -------------------- #

    def run_scheduler(self):

        while self.running:

            schedule.run_pending()

            time.sleep(1)