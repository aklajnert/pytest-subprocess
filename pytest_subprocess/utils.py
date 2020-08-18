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
            other = tuple(other.split(" "))
        elif isinstance(other, list):
            other = tuple(other)

        if other == self.command:
            # straightforward matching
            return True

        if len(other) < len(self.command):
            return False

        for (other_item, self_item) in zip(other, self.command):
            if other_item != self_item and not isinstance(self_item, Any):
                return False

        return True

    def __hash__(self):
        return hash(self.command)

    def __repr__(self):
        return self.command

    def __str__(self):
        return str(self.command)


class Any:
    """Wildcard definition class."""

    def __init__(self, arguments=0):
        self.arguments = arguments
