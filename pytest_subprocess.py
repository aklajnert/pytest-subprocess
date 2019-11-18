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
    """
    Raised when the attempted command wasn't registered before.
    Use `fake_process.allow_unregistered(True)` if you want to use real subprocess.
    """


class ProcessDispatcher:
    """Main class for handling processes."""

    process_list = []
    built_in_popen = None
    _allow_unregistered = False

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
    def dispatch(cls, command, *args, **kwargs) -> None:
        process = next(
            (
                proc.processes.get(command)
                for proc in reversed(cls.process_list)
                if command in proc.processes
            ),
            None,
        )

        if process is None:
            if not cls._allow_unregistered:
                raise ProcessNotRegisteredError(
                    "The process '{}' was not registered.".format(
                        command if isinstance(command, str) else " ".join(command)
                    )
                )
            else:
                return cls.built_in_popen(command, *args, **kwargs)

        result = process.handle()
        return result

    @classmethod
    def allow_unregistered(cls, allow):
        cls._allow_unregistered = allow


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

    def allow_unregistered(cls, allow):
        ProcessDispatcher.allow_unregistered(allow)

    @classmethod
    def context(cls) -> 'Process':
        return cls()


@pytest.fixture
def fake_process():
    with Process() as process:
        yield process
