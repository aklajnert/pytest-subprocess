import threading

import typing

ARGUMENT = typing.Union[str, "Any"]

class Thread(threading.Thread):
    exception: typing.Optional[Exception] = None
    def run(self) -> None: ...

class Command:
    command: typing.Tuple[str, ...]
    def __init__(
        self,
        command: typing.Union[typing.Tuple[ARGUMENT, ...], typing.List[ARGUMENT], str],
    ) -> None: ...

class Any:
    min: typing.Optional[int]
    max: typing.Optional[int]
    def __init__(self, min: typing.Optional[int] = 0, max: typing.Optional[int] = 0) -> None: ...
