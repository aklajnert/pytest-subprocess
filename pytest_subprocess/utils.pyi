import threading

import typing


class Thread(threading.Thread):

    exception: typing.Optional[Exception] = None

    def run(self) -> None: ...
