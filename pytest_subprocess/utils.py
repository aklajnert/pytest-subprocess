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

        command_index = 0
        command_elem = self.command[command_index]
        next_command_elem = self._get_next_elem(command_index)
        for elem in other:
            if isinstance(command_elem, Any):
                if command_elem.arguments == -1:
                    if next_command_elem != elem:
                        continue
            else:
                if elem != command_elem:
                    return False

            command_index += 1
            command_elem = next_command_elem
            next_command_elem = self._get_next_elem(command_index)

        return command_index == len(self.command) - 1

    def _get_next_elem(self, command_index):
        return (
            self.command[command_index + 1]
            if len(self.command) > command_index + 1
            else None
        )

    def __hash__(self):
        return hash(self.command)

    def __repr__(self):
        return self.command

    def __str__(self):
        return str(self.command)


class Any:
    """Wildcard definition class."""

    def __init__(self, arguments=-1):
        self.arguments = arguments
