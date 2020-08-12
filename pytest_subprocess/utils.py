import threading


class Thread(threading.Thread):
    """Custom thread class to capture exceptions"""

    exception = None

    def run(self):
        try:
            super().run()
        except Exception as exc:
            self.exception = exc


class Command:
    """Command definition class."""

    def __init__(self, command):
        if isinstance(command, str):
            command = tuple(command.split(" "))
        if isinstance(command, list):
            command = tuple(command)
        elif not isinstance(command, tuple):
            raise TypeError("Command can be only of type string, list or tuple.")
        self.command = command

    def __eq__(self, other):
        if isinstance(other, str):
            return other == " ".join(self.command)
        elif isinstance(other, list):
            return tuple(other) == self.command
        return other == self.command

    def __hash__(self):
        return hash(self.command)

    def __repr__(self):
        return self.command

    def __str__(self):
        return str(self.command)
