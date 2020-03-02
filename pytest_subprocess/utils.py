import threading


class Thread(threading.Thread):
    """Custom thread class to capture exceptions"""

    exception = None

    def run(self):
        try:
            super().run()
        except Exception as exc:
            self.exception = exc
