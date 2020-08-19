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
        min_ = None
        max_ = None
        for elem in other:
            if isinstance(command_elem, Any):
                if command_elem.min == None and command_elem.max == None:
                    if next_command_elem != elem:
                        continue
                else:
                    if min_ == None:
                        min_ = command_elem.min
                    if max_ == None:
                        max_ = command_elem.max

                    if next_command_elem == elem or next_command_elem is None:
                        if not self._thresholds_ok(min_, max_):
                            return False

                    max_ -= 1
                    if next_command_elem is None:
                        continue
            else:
                if elem != command_elem:
                    return False

            command_index += 1
            command_elem = next_command_elem
            next_command_elem = self._get_next_elem(command_index)

        return (
            self._thresholds_ok(min_, max_) and command_index == len(self.command) - 1
        )

    def _get_next_elem(self, command_index):
        return (
            self.command[command_index + 1]
            if len(self.command) > command_index + 1
            else None
        )

    def _thresholds_ok(self, min_, max_):
        if min_ is not None and min_ >= 0:
            return False
        if max_ is not None and max_ < 0:
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

    def __init__(self, *, min=None, max=None):
        if min is not None and max is not None and min > max:
            raise AttributeError("min cannot be greater than max")
        self.min = min
        self.max = max
