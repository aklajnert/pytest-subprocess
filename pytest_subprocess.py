# -*- coding: utf-8 -*-

import pytest


class FakePopen:
    """The base class that fakes the real subprocess"""

    def __init__(self, command):
        self.command = command


class ProcessDispatcher:
    """Main class for handling processes."""

    process_list = []

    @classmethod
    def register(cls, process):
        cls.process_list.append(process)

    @classmethod
    def deregister(cls, process):
        cls.process_list.remove(process)


class Process:
    """Class responsible for tracking the processes"""

    def __init__(self):
        self.processes = dict()

    def register_subprocess(self, command):
        if isinstance(command, list):
            command = tuple(command)

        self.processes[command] = FakePopen(command)

    def __enter__(self):
        ProcessDispatcher.register(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        ProcessDispatcher.deregister(self)


@pytest.fixture
def process():
    with Process() as process:
        yield process
