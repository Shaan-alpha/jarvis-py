import time


class SessionManager:

    def __init__(self, timeout=20):

        self.active = False
        self.timeout = timeout
        self.last_interaction = time.time()

    def activate(self):

        self.active = True
        self.update_interaction()

    def deactivate(self):

        self.active = False

    def update_interaction(self):

        self.last_interaction = time.time()

    def is_expired(self):

        return (
            time.time() - self.last_interaction
        ) > self.timeout