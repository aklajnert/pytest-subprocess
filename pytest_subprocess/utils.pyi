import threading

import typing


class Thread(threading.Thread):

    exception: typing.Optional[Exception] = None

    def run(self) -> None: ...

class Command:
    command: typing.Tuple[str, ...]

    def __init__(self, command: typing.Union[typing.Tuple[str, ...], str]) -> None: ...
