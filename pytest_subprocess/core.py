# -*- coding: utf-8 -*-
import io
import os
import subprocess
import sys
import threading
import time
from collections import defaultdict
from collections import deque
from copy import deepcopy


def _ensure_hashable(input):
    if isinstance(input, list):
        return tuple(input)
    return input


class FakePopen:
    """Base class that fakes the real subprocess.Popen()"""

    stdout = None
    stderr = None
    returncode = None
    text_mode = False
    pid = 0

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
        """Setup the FakePopen instance based on a real Popen arguments."""
        self.__universal_newlines = kwargs.get("universal_newlines", None)
        text = kwargs.get("text", None)

        if text and sys.version_info < (3, 7):
            raise TypeError("__init__() got an unexpected keyword argument 'text'")

        self.text_mode = bool(text or self.__universal_newlines)

        # validation taken from the real subprocess
        if (
            text is not None
            and self.__universal_newlines is not None
            and bool(self.__universal_newlines) != bool(text)
        ):
            raise subprocess.SubprocessError(
                "Cannot disambiguate when both text "
                "and universal_newlines are supplied but "
                "different. Pass one or the other."
            )

        if kwargs.get("stdout") == subprocess.PIPE:
            self.stdout = self._prepare_buffer(self.__stdout)
        stderr = kwargs.get("stderr")
        if stderr == subprocess.STDOUT:
            self.stdout = self._prepare_buffer(self.__stderr, self.stdout)
        elif stderr == subprocess.PIPE:
            self.stderr = self._prepare_buffer(self.__stderr)

    def _prepare_buffer(self, input, io_base=None):
        linesep = self._convert(os.linesep)
        if io_base is None:
            io_base = io.StringIO() if self.text_mode else io.BytesIO()

        if input is None:
            return io_base

        if isinstance(input, (list, tuple)):
            input = linesep.join(map(self._convert, input))

        if isinstance(input, str) and not self.text_mode:
            input = input.encode()

        if isinstance(input, bytes) and self.text_mode:
            input = input.decode()

        if not input.endswith(linesep):
            input += linesep

        if self.text_mode and self.__universal_newlines:
            input = input.replace("\r\n", "\n")
        io_base.write(input)
        return io_base

    def _convert(self, input):
        if isinstance(input, bytes) and self.text_mode:
            return input.decode()
        if isinstance(input, str) and not self.text_mode:
            return input.encode()
        return input

    def _wait(self, wait_period):
        time.sleep(wait_period)
        if self.returncode is None:
            self._finish_process()

    def run_thread(self):
        """Run the user-defined callback or wait in a thread."""
        if self.__wait is None and self.__callback is None:
            self._finish_process()
        else:
            if self.__callback:
                self.__thread = threading.Thread(target=self.__callback, args=(self,))
            else:
                self.__thread = threading.Thread(target=self._wait, args=(self.__wait,))
            self.__thread.start()

    def _finish_process(self):
        self.returncode = self.__returncode

        if self.stdout:
            self.stdout.seek(0)

        if self.stderr:
            self.stderr.seek(0)


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
    _pid = 0

    @classmethod
    def register(cls, process):
        if not cls.process_list:
            cls.built_in_popen = subprocess.Popen
            subprocess.Popen = cls.dispatch
        cls._cache[process] = {
            proc: deepcopy(proc.definitions) for proc in cls.process_list
        }
        cls.process_list.append(process)

    @classmethod
    def deregister(cls, process):
        cls.process_list.remove(process)
        cache = cls._cache.pop(process)
        for proc, processes in cache.items():
            proc.definitions = processes
        if not cls.process_list:
            subprocess.Popen = cls.built_in_popen
            cls.built_in_popen = None

    @classmethod
    def dispatch(cls, command, **kwargs):
        """This method will be used instead of the subprocess.Popen()"""
        command = _ensure_hashable(command)

        processes, process_instance = cls._get_process(command)

        if not processes:
            if not cls._allow_unregistered:
                raise ProcessNotRegisteredError(
                    "The process '%s' was not registered."
                    % (command if isinstance(command, str) else " ".join(command),)
                )
            else:
                return cls.built_in_popen(command, **kwargs)

        process = processes.popleft()
        if not processes and process_instance:
            if cls._keep_last_process:
                processes.append(process)
            else:
                del process_instance.definitions[command]

        cls._pid += 1
        if process is True:
            return cls.built_in_popen(command, **kwargs)

        result = FakePopen(**process)
        result.pid = cls._pid
        result.configure(**kwargs)
        result.run_thread()
        return result

    @classmethod
    def _get_process(cls, command):
        for proc in reversed(cls.process_list):
            processes = proc.definitions.get(command)
            process_instance = proc
            if processes:
                return processes, process_instance
        return None, None

    @classmethod
    def allow_unregistered(cls, allow):
        cls._allow_unregistered = allow

    @classmethod
    def keep_last_process(cls, keep):
        cls._keep_last_process = keep


class IncorrectProcessDefinition(Exception):
    """Raised when the register_subprocess() has been called with wrong arguments"""


class FakeProcess:
    """Class responsible for tracking the processes"""

    def __init__(self):
        self.definitions = defaultdict(deque)

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
        """
        Main method for registering the subprocess instances.

        Args:
            command: register the command that will be faked
            stdout: value of the standard output
            stderr: value of the error output
            returncode: return code of the faked process
            wait: artificially wait for the process to finish
            callback: function that will be executed instead of the process
            occurrences: allow multiple usages of the same command
        """
        if wait is not None and callback is not None:
            raise IncorrectProcessDefinition(
                "The 'callback' and 'wait' arguments cannot be used "
                "together. Add sleep() to your callback instead."
            )
        command = _ensure_hashable(command)
        self.definitions[command].extend(
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

    def pass_command(self, command, occurrences=1):
        """
        Allow to use a real subprocess together with faked ones.

        Args:
            command: allow to execute the supplied command
            occurrences: allow multiple usages of the same command
        """
        command = _ensure_hashable(command)
        self.definitions[command].extend([True] * occurrences)

    def __enter__(self):
        ProcessDispatcher.register(self)
        return self

    def __exit__(self, *args, **kwargs):
        ProcessDispatcher.deregister(self)

    def allow_unregistered(cls, allow):
        """
        Allow / block unregistered processes execution. When allowed, the real
        subprocesses will be called. Blocking will raise the exception.

        Args:
            allow: decide whether the unregistered process shall be allowed
        """
        ProcessDispatcher.allow_unregistered(allow)

    @classmethod
    def keep_last_process(cls, keep):
        """
        Keep last process definition from being removed. That can allow / block
        multiple execution of the same command.

        Args:
            keep: decide whether last process shall be kept
        """
        ProcessDispatcher.keep_last_process(keep)

    @classmethod
    def context(cls):
        """Return a new FakeProcess instance to use it as a context manager."""
        return cls()
