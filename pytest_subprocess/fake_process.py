"""FakeProcess class declaration"""
from collections import defaultdict
from collections import deque
from typing import Any as AnyType
from typing import Callable
from typing import ClassVar
from typing import DefaultDict
from typing import Deque
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from typing import Union

from . import exceptions
from .process_dispatcher import ProcessDispatcher
from .process_recorder import ProcessRecorder
from .types import COMMAND
from .types import OPTIONAL_TEXT_OR_ITERABLE
from .utils import Any
from .utils import Command
from .utils import Program


class FakeProcess:
    """Main class responsible for process operations"""

    any: ClassVar[Type[Any]] = Any
    program: ClassVar[Type[Program]] = Program

    def __init__(self) -> None:
        self.definitions: DefaultDict[Command, Deque[Union[Dict, bool]]] = defaultdict(
            deque
        )
        self.calls: Deque[COMMAND] = deque()
        self._allow_unregistered: bool = False
        self._keep_last_process: bool = False

        self.exceptions = exceptions

    def register(
        self,
        command: COMMAND,
        stdout: OPTIONAL_TEXT_OR_ITERABLE = None,
        stderr: OPTIONAL_TEXT_OR_ITERABLE = None,
        returncode: int = 0,
        wait: Optional[float] = None,
        callback: Optional[Callable] = None,
        callback_kwargs: Optional[Dict[str, AnyType]] = None,
        signal_callback: Optional[Callable] = None,
        occurrences: int = 1,
        stdin_callable: Optional[Callable] = None,
    ) -> ProcessRecorder:
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
            raise exceptions.IncorrectProcessDefinition(
                "The 'callback' and 'wait' arguments cannot be used "
                "together. Add sleep() to your callback instead."
            )
        if not isinstance(command, Command):
            command = Command(command)

        recorder = ProcessRecorder()
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
                    "signal_callback": signal_callback,
                    "stdin_callable": stdin_callable,
                    "recorder": recorder,
                }
            ]
            * occurrences
        )

        return recorder

    register_subprocess = register

    def pass_command(
        self,
        command: COMMAND,
        occurrences: int = 1,
    ) -> None:
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

    def allow_unregistered(self, allow: bool) -> None:
        """
        Allow / block unregistered processes execution. When allowed, the real
        subprocesses will be called. Blocking will raise the exception.

        Args:
            allow: decide whether the unregistered process shall be allowed
        """
        self._allow_unregistered = allow

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

    def keep_last_process(self, keep: bool) -> None:
        """
        Keep last process definition from being removed. That can allow / block
        multiple execution of the same command.

        Args:
            keep: decide whether last process shall be kept
        """
        self._keep_last_process = keep

    @classmethod
    def context(cls) -> "FakeProcess":
        """Return a new FakeProcess instance to use it as a context manager."""
        return cls()
