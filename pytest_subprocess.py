# -*- coding: utf-8 -*-
import typing

import pytest

process_list: typing.List["Process"] = []


class FakePopen:
    """The base class that fakes the real subprocess"""

    def __init__(self, command: typing.Union[typing.Tuple[str], str]):
        self.command: typing.Union[typing.List[str], typing.Tuple[str], str] = command


class Process:
    """Class responsible for tracking the processes"""

    def __init__(self):
        self.processes: typing.Dict[
            typing.Union[str, typing.Tuple[str]], FakePopen
        ] = dict()

    def register_subprocess(
        self, command: typing.Union[typing.List[str], typing.Tuple[str], str]
    ):
        if isinstance(command, list):
            command = tuple(command)

        self.processes[command] = FakePopen(command)

    def __enter__(self) -> "Process":
        process_list.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        process_list.remove(self)


@pytest.fixture
def process() -> Process:
    with Process():
        yield
