# -*- coding: utf-8 -*-
import io
import os
import subprocess
import threading
import time
from collections import defaultdict
from collections import deque
from copy import deepcopy

import pytest

LINESEP = os.linesep.encode()


def _ensure_hashable(input):
    if isinstance(input, list):
        return tuple(input)
    return input


class FakePopen:
    """The base class that fakes the real subprocess"""

    stdout = None
    stderr = None
    returncode = None

    def __init__(
        self,
        command,
        stdout=None,
        stderr=None,
        returncode=0,
        wait=None,
        callback=None,
        **_
    ):
        self.args = command
        self.__stdout = stdout
        self.__stderr = stderr
        self.__returncode = returncode
        self.__wait = wait
        self.__thread = None
        self.__callback = callback

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def communicate(self, input=None, timeout=None):
        return (
            self.stdout.getvalue() if self.stdout else None,
            self.stderr.getvalue() if self.stderr else None,
        )

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        # todo: make it smarter and aware of time left
        if timeout and timeout < self.__wait:
            raise subprocess.TimeoutExpired(self.args, timeout)
        if self.__thread is not None:
            self.__thread.join()
        return self.returncode

    def configure(self, **kwargs):
        if kwargs.get("stdout") == subprocess.PIPE:
            self.stdout = self._prepare_buffer(self.__stdout)
        stderr = kwargs.get("stderr")
        if stderr == subprocess.STDOUT:
            self.stdout = self._prepare_buffer(self.__stderr, self.stdout)
        elif stderr == subprocess.PIPE:
            self.stderr = self._prepare_buffer(self.__stderr)

    @staticmethod
    def _prepare_buffer(input, io_base=None):
        if io_base is None:
            io_base = io.BytesIO()

        if input is None:
            return io_base

        if isinstance(input, (list, tuple)):
            input = LINESEP.join(
                line.encode() if isinstance(line, str) else line for line in input
            )

        if isinstance(input, str):
            input = input.encode()

        if not input.endswith(LINESEP):
            input += LINESEP

        io_base.write(input)
        return io_base

    def _wait(self, wait_period):
        time.sleep(wait_period)
        if self.returncode is None:
            self.returncode = self.__returncode

    def run_thread(self):
        if self.__wait is None and self.__callback is None:
            self.returncode = self.__returncode
        else:
            if self.__callback:
                self.__thread = threading.Thread(target=self.__callback, args=(self,))
            else:
                self.__thread = threading.Thread(target=self._wait, args=(self.__wait,))
            self.__thread.start()


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
    _cache = dict()
    _keep_last_process = False

    @classmethod
    def register(cls, process):
        if not cls.process_list:
            cls.built_in_popen = subprocess.Popen
            subprocess.Popen = cls.dispatch
        cls._cache[process] = {
            proc: deepcopy(proc.processes) for proc in cls.process_list
        }
        cls.process_list.append(process)

    @classmethod
    def deregister(cls, process):
        cls.process_list.remove(process)
        cache = cls._cache.pop(process)
        for proc, processes in cache.items():
            proc.processes = processes
        if not cls.process_list:
            subprocess.Popen = cls.built_in_popen
            cls.built_in_popen = None

    @classmethod
    def dispatch(cls, command, **kwargs):
        command = _ensure_hashable(command)

        processes = None
        process_instance = None
        for proc in reversed(cls.process_list):
            processes = proc.processes.get(command)
            process_instance = proc
            if processes:
                break

        if not processes:
            if not cls._allow_unregistered:
                raise ProcessNotRegisteredError(
                    "The process '{}' was not registered.".format(
                        command if isinstance(command, str) else " ".join(command)
                    )
                )
            else:
                return cls.built_in_popen(command, **kwargs)

        process = processes.popleft()
        if not processes and process_instance:
            if cls._keep_last_process:
                processes.append(process)
            else:
                del process_instance.processes[command]

        result = FakePopen(**process)
        result.configure(**kwargs)
        result.run_thread()
        return result

    @classmethod
    def allow_unregistered(cls, allow):
        cls._allow_unregistered = allow

    @classmethod
    def keep_last_process(cls, leave):
        cls._keep_last_process = leave


class IncorrectProcessDefinition(Exception):
    """Raised when the register_subprocess() has been called with wrong arguments"""


class Process:
    """Class responsible for tracking the processes"""

    def __init__(self):
        self.processes = defaultdict(deque)

    def register_subprocess(
        self,
        command,
        stdout=None,
        stderr=None,
        returncode=0,
        wait=None,
        callback=None,
        occurrences=1,
    ):
        if wait is not None and callback is not None:
            raise IncorrectProcessDefinition(
                "The 'callback' and 'wait' arguments cannot be used "
                "together. Add sleep() to your callback instead."
            )
        command = _ensure_hashable(command)
        self.processes[command].extend(
            [
                {
                    "command": command,
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": returncode,
                    "wait": wait,
                    "callback": callback,
                }
            ]
            * occurrences
        )

    def __enter__(self):
        ProcessDispatcher.register(self)
        return self

    def __exit__(self, *args, **kwargs):
        ProcessDispatcher.deregister(self)

    def allow_unregistered(cls, allow):
        ProcessDispatcher.allow_unregistered(allow)

    @classmethod
    def keep_last_process(cls, leave):
        ProcessDispatcher.keep_last_process(leave)

    @classmethod
    def context(cls):
        return cls()


@pytest.fixture
def fake_process():
    with Process() as process:
        yield process
