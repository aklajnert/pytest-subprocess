# -*- coding: utf-8 -*-
import typing

import pytest

class FakePopen:
    command: typing.Union[typing.List[str], typing.Tuple[str], str]
    def __init__(self, command: typing.Union[typing.Tuple[str], str]): ...
    def handle(self) -> None: ...

class ProcessDispatcher:
    process_list: typing.List["Process"]
    @classmethod
    def register(cls, process: "Process"): ...
    @classmethod
    def deregister(cls, process: "Process"): ...
    @classmethod
    def dispatch(
        cls,
        command: typing.Union[typing.Tuple[str], str],
        *_: typing.Any,
        **__: typing.Any
    ) -> None: ...

class Process:

    processes: typing.Dict[typing.Union[str, typing.Tuple[str]], FakePopen]
    def __init__(self) -> None: ...
    def register_subprocess(
        self, command: typing.Union[typing.List[str], typing.Tuple[str], str]
    ): ...
    def __enter__(self) -> "Process": ...
    def __exit__(self, exc_type, exc_val, exc_tb): ...

@pytest.fixture
def process() -> Process: ...
