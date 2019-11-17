# -*- coding: utf-8 -*-
import subprocess

import pytest


class FakePopen:
    """The base class that fakes the real subprocess"""

    def __init__(self, command):
        self.command = command

    def handle(self):
        pass


class ProcessNotRegisteredError(Exception):
    """Raised when the attempted command wasn't registered before."""


class ProcessDispatcher:
    """Main class for handling processes."""

    process_list = []
    built_in_popen = None

    @classmethod
    def register(cls, process):
        if not cls.process_list:
            cls.built_in_popen = subprocess.Popen
            subprocess.Popen = cls.dispatch
        cls.process_list.append(process)

    @classmethod
    def deregister(cls, process):
        cls.process_list.remove(process)
        if not cls.process_list:
            subprocess.Popen = cls.built_in_popen
            cls.built_in_popen = None

    @classmethod
    def dispatch(cls, command, *_, **__) -> None:
        process = next(
            (
                proc.processes.get(command)
                for proc in cls.process_list
                if command in proc.processes
            ),
            None,
        )

        if process is None:
            raise ProcessNotRegisteredError(
                f"The process '%s' was not registered."
                % (command if isinstance(command, str) else " ".join(command))
            )

        result = process.handle()
        return result


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
