# -*- coding: utf-8 -*-
import io
import os
import subprocess
import sys
import time
from collections import defaultdict
from collections import deque
from copy import deepcopy
from typing import Any as AnyType
from typing import Callable
from typing import DefaultDict
from typing import Deque
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from typing import Union

from .utils import Any
from .utils import Command
from .utils import Thread

OPTIONAL_TEXT = Union[str, bytes, None]
OPTIONAL_TEXT_OR_ITERABLE = Union[
    str, bytes, None, Sequence[Union[str, bytes]],
]
BUFFER = Union[None, io.BytesIO, io.StringIO]
ARGUMENT = Union[str, Any]
COMMAND = Union[Sequence[ARGUMENT], str, Command]


class PluginInternalError(Exception):
    """Raised in case of an internal error in the plugin"""


class FakePopen:
    """Base class that fakes the real subprocess.Popen()"""

    stdout: BUFFER = None
    stderr: BUFFER = None
    returncode: Optional[int] = None
    text_mode: bool = False
    pid: int = 0

    def __init__(
        self,
        command: Union[
            Union[bytes, str],
            Sequence[Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]"]],
        ],
        stdout: OPTIONAL_TEXT_OR_ITERABLE = None,
        stderr: OPTIONAL_TEXT_OR_ITERABLE = None,
        returncode: int = 0,
        wait: Optional[float] = None,
        callback: Optional[Callable] = None,
        callback_kwargs: Optional[Dict[str, AnyType]] = None,
        stdin_callable: Optional[Callable] = None,
        **_: Dict[str, AnyType]
    ) -> None:
        self.args = command
        self.__stdout: OPTIONAL_TEXT_OR_ITERABLE = stdout
        self.__stderr: OPTIONAL_TEXT_OR_ITERABLE = stderr
        self.__returncode: Optional[int] = returncode
        self.__wait: Optional[float] = wait
        self.__thread: Optional[Thread] = None
        self.__callback: Optional[Optional[Callable]] = callback
        self.__callback_kwargs: Optional[Dict[str, AnyType]] = callback_kwargs
        self.__stdin_callable: Optional[Optional[Callable]] = stdin_callable

    def __enter__(self) -> "FakePopen":
        return self

    def __exit__(self, *args: List, **kwargs: Dict) -> None:
        if self.__thread and self.__thread.exception:
            raise self.__thread.exception

    def communicate(
        self, input: OPTIONAL_TEXT = None, timeout: Optional[float] = None
    ) -> Tuple[AnyType, AnyType]:
        if input and self.__stdin_callable:
            callable_output = self.__stdin_callable(input)
            if isinstance(callable_output, dict):
                self.stdout = self._extend_stream_from_dict(
                    callable_output, "stdout", self.stdout
                )
                self.stderr = self._extend_stream_from_dict(
                    callable_output, "stderr", self.stderr
                )

        if self.__thread is not None:
            self.__thread.join(timeout)

        return (
            self.stdout.getvalue() if self.stdout else None,
            self.stderr.getvalue() if self.stderr else None,
        )

    def _extend_stream_from_dict(
        self, dictionary: Dict[str, AnyType], key: str, stream: BUFFER
    ) -> BUFFER:
        data = dictionary.get(key)
        if data:
            return self._prepare_buffer(input=data, io_base=stream)
        return None

    def poll(self) -> Optional[int]:
        return self.returncode

    def wait(self, timeout: Optional[float] = None) -> int:
        if timeout and self.__wait and timeout < self.__wait:
            self.__wait -= timeout
            raise subprocess.TimeoutExpired(self.args, timeout)
        if self.__thread is not None:
            self.__thread.join()
            if self.returncode is None and self.__returncode is not None:
                self.returncode = self.__returncode
            if self.__thread.exception:
                raise self.__thread.exception
        if self.returncode is None:
            raise PluginInternalError
        return self.returncode

    def configure(self, **kwargs: Optional[Dict]) -> None:
        """Setup the FakePopen instance based on a real Popen arguments."""
        self.__universal_newlines = kwargs.get("universal_newlines", None)
        text = kwargs.get("text", None)
        encoding = kwargs.get("encoding", None)
        errors = kwargs.get("errors", None)

        if text and sys.version_info < (3, 7):
            raise TypeError("__init__() got an unexpected keyword argument 'text'")

        self.text_mode = bool(text or self.__universal_newlines or encoding or errors)

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
        if stderr == subprocess.STDOUT and self.__stderr:
            self.stdout = self._prepare_buffer(self.__stderr, self.stdout)
        elif stderr == subprocess.PIPE:
            self.stderr = self._prepare_buffer(self.__stderr)

    def _prepare_buffer(
        self, input: OPTIONAL_TEXT_OR_ITERABLE, io_base: BUFFER = None,
    ) -> Union[io.BytesIO, io.StringIO]:
        linesep = self._convert(os.linesep)

        if isinstance(input, (list, tuple)):
            # need to disable mypy, as input and linesep are unions,
            # mypy thinks that the types might be incompatible, but
            # the _convert() function handles that
            input = linesep.join(map(self._convert, input))  # type: ignore

            # Add trailing newline if data is present.
            if input:
                # same reason to disable mypy as above
                input += linesep  # type: ignore

        if isinstance(input, str) and not self.text_mode:
            input = input.encode()

        if isinstance(input, bytes) and self.text_mode:
            input = input.decode()

        if input and self.__universal_newlines and isinstance(input, str):
            input = input.replace("\r\n", "\n")

        if io_base is not None:
            # same reason for disabling mypy as in `input = linesep.join...`:
            # both are union so could be incompatible if not _convert()
            input = io_base.getvalue() + (input)  # type: ignore

        io_base = io.StringIO() if self.text_mode else io.BytesIO()

        if input is None:
            return io_base

        # similar as above - mypy has to be disabled because unions
        io_base.write(input)  # type: ignore
        return io_base

    def _convert(self, input: Union[str, bytes]) -> Union[str, bytes]:
        if isinstance(input, bytes) and self.text_mode:
            return input.decode()
        if isinstance(input, str) and not self.text_mode:
            return input.encode()
        return input

    def _wait(self, wait_period: float) -> None:
        time.sleep(wait_period)
        if self.returncode is None:
            self._finish_process()

    def run_thread(self) -> None:
        """Run the user-defined callback or wait in a thread."""
        if self.__wait is None and self.__callback is None:
            self._finish_process()
        else:
            if self.__callback:
                self.__thread = Thread(
                    target=self.__callback,
                    args=(self,),
                    kwargs=self.__callback_kwargs or {},
                )
            else:
                self.__thread = Thread(target=self._wait, args=(self.__wait,))
            self.__thread.start()

    def _finish_process(self) -> None:
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

    process_list: List["FakeProcess"] = []
    built_in_popen: Optional[Optional[Callable]] = None
    _allow_unregistered: bool = False
    _cache: Dict["FakeProcess", Dict["FakeProcess", AnyType]] = dict()
    _keep_last_process: bool = False
    _pid: int = 0

    @classmethod
    def register(cls, process: "FakeProcess") -> None:
        if not cls.process_list:
            cls.built_in_popen = subprocess.Popen
            subprocess.Popen = cls.dispatch  # type: ignore
        cls._cache[process] = {
            proc: deepcopy(proc.definitions) for proc in cls.process_list
        }
        cls.process_list.append(process)

    @classmethod
    def deregister(cls, process: "FakeProcess") -> None:
        cls.process_list.remove(process)
        cache = cls._cache.pop(process)
        for proc, processes in cache.items():
            proc.definitions = processes
        if not cls.process_list:
            subprocess.Popen = cls.built_in_popen  # type: ignore
            cls.built_in_popen = None

    @classmethod
    def dispatch(cls, command: COMMAND, **kwargs: Optional[Dict]) -> FakePopen:
        """This method will be used instead of the subprocess.Popen()"""
        command_instance, processes, process_instance = cls._get_process(command)

        if process_instance:
            process_instance.calls.append(command)

        if not processes:
            if not cls._allow_unregistered:
                raise ProcessNotRegisteredError(
                    "The process '%s' was not registered."
                    % (
                        command
                        if isinstance(command, str)
                        else " ".join(str(item) for item in command),
                    )
                )
            else:
                if cls.built_in_popen is None:
                    raise PluginInternalError
                return cls.built_in_popen(command, **kwargs)  # type: ignore

        process = processes.popleft()
        if not processes and process_instance is not None:
            if cls._keep_last_process:
                processes.append(process)
            elif command_instance:
                del process_instance.definitions[command_instance]

        cls._pid += 1
        if isinstance(process, bool):
            # real process will be called
            return cls.built_in_popen(command, **kwargs)  # type: ignore

        # Update the command with the actual command specified by the caller.
        # This will ensure that Command objects do not end up unexpectedly in
        # caller's objects (e.g. proc.args, CalledProcessError.cmd). Take care
        # to preserve the dict that may still be referenced when using
        # keep_last_process.
        fake_popen_kwargs = process.copy()
        fake_popen_kwargs["command"] = command

        result = FakePopen(**fake_popen_kwargs)
        result.pid = cls._pid
        result.configure(**kwargs)
        result.run_thread()
        return result

    @classmethod
    def _get_process(
        cls, command: COMMAND
    ) -> Tuple[
        Optional[Command], Optional[Deque[Union[dict, bool]]], Optional["FakeProcess"]
    ]:
        for proc in reversed(cls.process_list):
            command_instance, processes = next(
                (
                    (key, value)
                    for key, value in proc.definitions.items()
                    if key == command
                ),
                (None, None),
            )
            process_instance = proc
            if processes and isinstance(processes, deque):
                return command_instance, processes, process_instance
        return None, None, None

    @classmethod
    def allow_unregistered(cls, allow: bool) -> None:
        cls._allow_unregistered = allow

    @classmethod
    def keep_last_process(cls, keep: bool) -> None:
        cls._keep_last_process = keep


class IncorrectProcessDefinition(Exception):
    """Raised when the register_subprocess() has been called with wrong arguments"""


class FakeProcess:
    """Main class responsible for process operations"""

    any: Type[Any] = Any

    def __init__(self) -> None:
        self.definitions: DefaultDict[Command, Deque[Union[Dict, bool]]] = defaultdict(
            deque
        )
        self.calls: Deque[COMMAND] = deque()

    def register_subprocess(
        self,
        command: COMMAND,
        stdout: OPTIONAL_TEXT_OR_ITERABLE = None,
        stderr: OPTIONAL_TEXT_OR_ITERABLE = None,
        returncode: int = 0,
        wait: Optional[float] = None,
        callback: Optional[Callable] = None,
        callback_kwargs: Optional[Dict[str, AnyType]] = None,
        occurrences: int = 1,
        stdin_callable: Optional[Callable] = None,
    ) -> None:
        """
        Main method for registering the subprocess instances.

        Args:
            command: register the command that will be faked
            stdout: value of the standard output
            stderr: value of the error output
            returncode: return code of the faked process
            wait: artificially wait for the process to finish
            callback: function that will be executed instead of the process
            callback_kwargs: keyword arguments that will be passed into callback
            occurrences: allow multiple usages of the same command
            stdin_callable: function that will interact with stdin
        """
        if wait is not None and callback is not None:
            raise IncorrectProcessDefinition(
                "The 'callback' and 'wait' arguments cannot be used "
                "together. Add sleep() to your callback instead."
            )
        if not isinstance(command, Command):
            command = Command(command)
        self.definitions[command].extend(
            [
                {
                    "command": command,
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": returncode,
                    "wait": wait,
                    "callback": callback,
                    "callback_kwargs": callback_kwargs,
                    "stdin_callable": stdin_callable,
                }
            ]
            * occurrences
        )

    def pass_command(self, command: COMMAND, occurrences: int = 1,) -> None:
        """
        Allow to use a real subprocess together with faked ones.

        Args:
            command: allow to execute the supplied command
            occurrences: allow multiple usages of the same command
        """

        if not isinstance(command, Command):
            command = Command(command)
        self.definitions[command].extend([True] * occurrences)

    def __enter__(self) -> "FakeProcess":
        ProcessDispatcher.register(self)
        return self

    def __exit__(self, *args: List, **kwargs: Dict) -> None:
        ProcessDispatcher.deregister(self)

    def allow_unregistered(cls, allow: bool) -> None:
        """
        Allow / block unregistered processes execution. When allowed, the real
        subprocesses will be called. Blocking will raise the exception.

        Args:
            allow: decide whether the unregistered process shall be allowed
        """
        ProcessDispatcher.allow_unregistered(allow)

    def call_count(self, command: COMMAND) -> int:
        """
        Count how many times a certain command was called. Can be used
        together with `fake_process.any()`.

        Args:
            command: lookup command

        Returns:
            number of times a command was called
        """
        if not isinstance(command, Command):
            command_instance = Command(command)
        return len(tuple(filter(lambda elem: elem == command_instance, self.calls)))

    @classmethod
    def keep_last_process(cls, keep: bool) -> None:
        """
        Keep last process definition from being removed. That can allow / block
        multiple execution of the same command.

        Args:
            keep: decide whether last process shall be kept
        """
        ProcessDispatcher.keep_last_process(keep)

    @classmethod
    def context(cls) -> "FakeProcess":
        """Return a new FakeProcess instance to use it as a context manager."""
        return cls()
