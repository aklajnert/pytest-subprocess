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

        for (i, command_elem) in enumerate(self.command):
            if isinstance(command_elem, Any) and isinstance(
                self._get_next_command_elem(i), Any
            ):
                raise AttributeError("Cannot use `Any()` one after another.")

    def __eq__(self, other):
        if isinstance(other, str):
            other = other.split(" ")
        elif isinstance(other, tuple):
            other = list(other)

        if other == list(self.command):
            # straightforward matching
            return True

        other = list(other)
        for (i, command_elem) in enumerate(self.command):
            if isinstance(command_elem, Any):
                next_command_elem = self._get_next_command_elem(i)
                if next_command_elem is None:
                    if not self._are_thresholds_ok(command_elem, len(other)):
                        return False
                    return True
                else:
                    next_matching_elem = self._get_next_matching_elem_index(
                        other, next_command_elem
                    )
                    if next_matching_elem is None:
                        return False
                    else:
                        if not self._are_thresholds_ok(
                            command_elem, next_matching_elem
                        ):
                            return False

                        other = other[next_matching_elem:]
            else:
                if other.pop(0) != command_elem:
                    return False

        return len(other) == 0

    @staticmethod
    def _are_thresholds_ok(command_elem, value):
        if command_elem.max is not None and value > command_elem.max:
            return False
        if command_elem.min is not None and value < command_elem.min:
            return False
        return True

    def _get_next_command_elem(self, index):
        try:
            return self.command[index + 1]
        except IndexError:
            return None

    @staticmethod
    def _get_next_matching_elem_index(other, elem):
        return next(
            (i for i, other_elem in enumerate(other) if elem == other_elem), None
        )

    def __hash__(self):
        return hash(self.command)

    def __repr__(self):
        return str(self.command)

    def __str__(self):
        return str(self.command)


class Any:
    """Wildcard definition class."""

    def __init__(self, *, min=None, max=None):
        if min is not None and max is not None and min > max:
            raise AttributeError("min cannot be greater than max")
        self.min = min
        self.max = max

    def __repr__(self):
        return "Any (min={}, max={})".format(self.min, self.max)
