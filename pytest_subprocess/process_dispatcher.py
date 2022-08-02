"""ProcessDispatcher class declaration"""
import asyncio
import subprocess
import sys
import typing
from collections import deque
from copy import deepcopy
from functools import partial
from typing import Any as AnyType
from typing import Awaitable
from typing import Callable
from typing import Deque
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union

from . import asyncio_subprocess
from . import exceptions
from .fake_popen import AsyncFakePopen
from .fake_popen import FakePopen
from .types import COMMAND
from .utils import Command

if typing.TYPE_CHECKING:
    from .fake_process import FakeProcess


class ProcessDispatcher:
    """Main class for handling processes."""

    process_list: List["FakeProcess"] = []
    built_in_popen: Optional[Callable] = None
    built_in_async_subprocess: Optional[AnyType] = None
    _allow_unregistered: bool = False
    _cache: Dict["FakeProcess", Dict["FakeProcess", AnyType]] = dict()
    _keep_last_process: bool = False
    _pid: int = 0

    @classmethod
    def register(cls, process: "FakeProcess") -> None:
        if not cls.process_list:
            cls.built_in_popen = subprocess.Popen
            subprocess.Popen = cls.dispatch  # type: ignore

            cls.built_in_async_subprocess = asyncio.subprocess
            asyncio.create_subprocess_shell = cls.async_shell  # type: ignore
            asyncio.create_subprocess_exec = cls.async_exec  # type: ignore
            asyncio.subprocess = asyncio_subprocess

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

            if cls.built_in_async_subprocess is None:
                raise exceptions.PluginInternalError

            asyncio.subprocess = cls.built_in_async_subprocess
            asyncio.create_subprocess_shell = (
                cls.built_in_async_subprocess.create_subprocess_shell
            )
            asyncio.create_subprocess_exec = (
                cls.built_in_async_subprocess.create_subprocess_exec
            )
            cls.built_in_async_subprocess = None

    @classmethod
    def dispatch(
        cls, command: COMMAND, **kwargs: Optional[Dict]
    ) -> Union[FakePopen, subprocess.Popen]:
        """This method will be used instead of the subprocess.Popen()"""
        process = cls.__dispatch(command)

        if process is None:
            if cls.built_in_popen is None:
                raise exceptions.PluginInternalError

            popen: subprocess.Popen = cls.built_in_popen(command, **kwargs)
            return popen

        result = cls._prepare_instance(FakePopen, command, kwargs, process)
        if not isinstance(result, FakePopen):
            raise exceptions.PluginInternalError
        result.run_thread()
        return result

    @classmethod
    async def async_shell(
        cls, cmd: Union[str, bytes], **kwargs: Dict
    ) -> Union[AsyncFakePopen, asyncio.subprocess.Process]:
        """Replacement of  asyncio.create_subprocess_shell()"""
        if not isinstance(cmd, (str, bytes)):
            raise ValueError("cmd must be a string")
        method = partial(
            cls.built_in_async_subprocess.create_subprocess_shell,  # type: ignore
            cmd,
            **kwargs
        )
        if isinstance(cmd, bytes):
            cmd = cmd.decode()
        return await cls._call_async(cmd, method, kwargs)

    @classmethod
    async def async_exec(
        cls, program: Union[str, bytes], *args: Union[str, bytes], **kwargs: Dict
    ) -> Union[AsyncFakePopen, asyncio.subprocess.Process]:
        """Replacement of asyncio.create_subprocess_exec()"""
        if not isinstance(program, (str, bytes)):
            raise ValueError("program must be a string")

        method = partial(
            cls.built_in_async_subprocess.create_subprocess_exec,  # type: ignore
            program,
            *args,
            **kwargs
        )
        if isinstance(program, bytes):
            program = program.decode()
        command = [
            program,
            *[arg.decode() if isinstance(arg, bytes) else arg for arg in args],
        ]
        return await cls._call_async(command, method, kwargs)

    @classmethod
    async def _call_async(
        cls,
        command: COMMAND,
        async_method: Callable,
        kwargs: Dict,
    ) -> Union[AsyncFakePopen, asyncio.subprocess.Process]:
        process = cls.__dispatch(command)

        if process is None:
            if cls.built_in_async_subprocess is None:
                raise exceptions.PluginInternalError

            async_shell: Awaitable[asyncio.subprocess.Process] = async_method()
            return await async_shell

        if sys.platform == "win32" and isinstance(
            asyncio.get_event_loop_policy().get_event_loop(), asyncio.SelectorEventLoop
        ):
            raise NotImplementedError(
                "The SelectorEventLoop doesn't support subprocess"
            )

        result = cls._prepare_instance(AsyncFakePopen, command, kwargs, process)
        if not isinstance(result, AsyncFakePopen):
            raise exceptions.PluginInternalError
        result.run_thread()
        return result

    @classmethod
    def _prepare_instance(
        cls,
        klass: Union[Type[FakePopen], Type[AsyncFakePopen]],
        command: COMMAND,
        kwargs: dict,
        process: dict,
    ) -> Union[FakePopen, AsyncFakePopen]:
        # Update the command with the actual command specified by the caller.
        # This will ensure that Command objects do not end up unexpectedly in
        # caller's objects (e.g. proc.args, CalledProcessError.cmd). Take care
        # to preserve the dict that may still be referenced when using
        # keep_last_process.
        fake_popen_kwargs = process.copy()
        fake_popen_kwargs["command"] = command
        recorder = fake_popen_kwargs.pop("recorder")

        result = klass(**fake_popen_kwargs)
        recorder.calls.append(result)
        result.pid = cls._pid
        result.configure(**kwargs)
        return result

    @classmethod
    def __dispatch(cls, command: COMMAND) -> Optional[dict]:
        command_instance, processes, process_instance = cls._get_process(command)
        if process_instance:
            process_instance.calls.append(command)
        if not processes:
            if not cls.process_list[-1]._allow_unregistered:
                raise exceptions.ProcessNotRegisteredError(
                    "The process '%s' was not registered."
                    % (
                        command
                        if isinstance(command, str)
                        else " ".join(str(item) for item in command),
                    )
                )
            else:
                return None
        process = processes.popleft()
        if not processes and process_instance is not None:
            if cls.process_list[-1]._keep_last_process:
                processes.append(process)
            elif command_instance:
                del process_instance.definitions[command_instance]
        cls._pid += 1
        if isinstance(process, bool):
            # real process will be called
            return None
        return process

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
