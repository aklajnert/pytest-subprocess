import threading

import typing

ARGUMENT = typing.Union[str, "Any"]

class Thread(threading.Thread):

    exception: typing.Optional[Exception] = None

    def run(self) -> None: ...

class Command:
    command: typing.Tuple[str, ...]

    def __init__(self, command: typing.Union[typing.Tuple[ARGUMENT, ...], typing.List[ARGUMENT], str]) -> None: ...

class Any:
    def __init__(self, arguments:int=0) -> None: ...
