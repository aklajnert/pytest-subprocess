"""FakePopen class declaration"""
import asyncio
import collections.abc
import io
import os
import signal
import subprocess
import sys
import time
from functools import partial
from typing import Any as AnyType
from typing import Callable
from typing import Dict
from typing import IO
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

from . import exceptions
from .types import BUFFER
from .types import OPTIONAL_TEXT
from .types import OPTIONAL_TEXT_OR_ITERABLE
from .utils import Thread


if sys.platform.startswith("win") and sys.version_info < (3, 8):
    COMMAND_SEQ = Sequence[Union[str, bytes]]
else:
    COMMAND_SEQ = Sequence[Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]"]]


class FakePopen:
    """Base class that fakes the real subprocess.Popen()"""

    stdout: Optional[BUFFER] = None
    stderr: Optional[BUFFER] = None
    returncode: Optional[int] = None
    text_mode: bool = False
    pid: int = 0

    def __init__(
        self,
        command: Union[
            Union[bytes, str],
            COMMAND_SEQ,
        ],
        stdout: OPTIONAL_TEXT_OR_ITERABLE = None,
        stderr: OPTIONAL_TEXT_OR_ITERABLE = None,
        returncode: int = 0,
        wait: Optional[float] = None,
        callback: Optional[Callable] = None,
        callback_kwargs: Optional[Dict[str, AnyType]] = None,
        signal_callback: Optional[Callable] = None,
        stdin_callable: Optional[Callable] = None,
        **_: Dict[str, AnyType],
    ) -> None:
        if (
            not isinstance(command, (str, bytes))
            and sys.platform.startswith("win")
            and sys.version_info < (3, 8)
        ):
            for arg in command:
                if isinstance(arg, os.PathLike):
                    msg = f"argument of type {arg.__class__.__name__!r} is not iterable"
                    raise TypeError(msg)
        self.args = command
        self.__stdout: OPTIONAL_TEXT_OR_ITERABLE = stdout
        self.__stderr: OPTIONAL_TEXT_OR_ITERABLE = stderr
        self.__returncode: Optional[int] = returncode
        self.__wait: Optional[float] = wait
        self.__thread: Optional[Thread] = None
        self.__callback: Optional[Optional[Callable]] = callback
        self.__callback_kwargs: Optional[Dict[str, AnyType]] = callback_kwargs
        self.__signal_callback: Optional[Callable] = signal_callback
        self.__stdin_callable: Optional[Optional[Callable]] = stdin_callable
        self._signals: List[int] = []

    def __enter__(self) -> "FakePopen":
        return self

    def __exit__(self, *args: List, **kwargs: Dict) -> None:
        if self.__thread and self.__thread.exception:
            raise self.__thread.exception

    def communicate(
        self, input: OPTIONAL_TEXT = None, timeout: Optional[float] = None
    ) -> Tuple[AnyType, AnyType]:
        self._handle_stdin(input)
        self._finalize_thread(timeout)

        if isinstance(self.stdout, asyncio.StreamReader) or isinstance(
            self.stderr, asyncio.StreamReader
        ):
            raise exceptions.PluginInternalError

        return (
            self.stdout.getvalue() if self.stdout else None,
            self.stderr.getvalue() if self.stderr else None,
        )

    def _handle_stdin(self, input: OPTIONAL_TEXT) -> None:
        if input and self.__stdin_callable:
            callable_output = self.__stdin_callable(input)
            if isinstance(callable_output, dict):
                self.stdout = self._extend_stream_from_dict(
                    callable_output, "stdout", self.stdout
                )
                self.stderr = self._extend_stream_from_dict(
                    callable_output, "stderr", self.stderr
                )

    def _finalize_thread(self, timeout: Optional[float]) -> None:
        if self.__thread is None:
            return
        self.__thread.join(timeout)
        if self.returncode is None and self.__returncode is not None:
            self.returncode = self.__returncode
        if self.__thread.exception:
            raise self.__thread.exception

    def _extend_stream_from_dict(
        self, dictionary: Dict[str, AnyType], key: str, stream: Optional[BUFFER]
    ) -> Optional[BUFFER]:
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
        self._finalize_thread(timeout)
        if self.returncode is None:
            raise exceptions.PluginInternalError
        return self.returncode

    def send_signal(self, sig: int) -> None:
        self._signals.append(sig)
        if self.__signal_callback:
            self.__signal_callback(self, sig)

    def terminate(self) -> None:
        self.send_signal(signal.SIGTERM)

    def kill(self) -> None:
        if sys.platform == "win32":
            self.terminate()
        else:
            self.send_signal(signal.SIGKILL)

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

        stdout = kwargs.get("stdout")
        if stdout == subprocess.PIPE:
            self.stdout = self._prepare_buffer(self.__stdout)
        elif isinstance(stdout, (io.BufferedWriter, io.TextIOWrapper)):
            self._write_to_buffer(self.__stdout, stdout)
        stderr = kwargs.get("stderr")
        if stderr == subprocess.STDOUT and self.__stderr:
            assert self.stdout is not None
            self.stdout = self._prepare_buffer(self.__stderr, self.stdout)
        elif stderr == subprocess.PIPE:
            self.stderr = self._prepare_buffer(self.__stderr)
        elif isinstance(stderr, (io.BufferedWriter, io.TextIOWrapper)):
            self._write_to_buffer(self.__stderr, stderr)

    def _prepare_buffer(
        self,
        input: OPTIONAL_TEXT_OR_ITERABLE,
        io_base: Optional[BUFFER] = None,
    ) -> Union[io.BytesIO, io.StringIO, asyncio.StreamReader]:
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

        if (
            io_base
            and not isinstance(io_base, asyncio.StreamReader)
            and io_base.tell() == 0
        ):
            # same reason for disabling mypy as in `input = linesep.join...`:
            # both are union so could be incompatible if not _convert()
            input = io_base.getvalue() + (input)  # type: ignore

        if io_base is None:
            io_base = self._get_empty_buffer(self.text_mode)

        if input is None:
            return io_base

        # similar as above - mypy has to be disabled because unions
        if isinstance(io_base, asyncio.StreamReader):
            io_base.feed_data(self._data_to_bytes(input))
        else:
            io_base.write(input)  # type: ignore
        return io_base

    def _get_empty_buffer(self, text: bool) -> BUFFER:
        return io.StringIO() if text else io.BytesIO()

    def _to_bytes(self, data: Sequence[Union[str, bytes]]) -> Sequence[bytes]:
        return [elem if isinstance(elem, bytes) else elem.encode() for elem in data]

    def _data_to_bytes(self, data: OPTIONAL_TEXT_OR_ITERABLE) -> bytes:
        if isinstance(data, collections.abc.Sequence) and not isinstance(data, bytes):
            return b"\n".join(
                (item if isinstance(item, bytes) else item.encode() for item in data)
            )
        if isinstance(data, str):
            return data.encode()
        if not data:
            return b""
        return data

    def _write_to_buffer(self, data: OPTIONAL_TEXT_OR_ITERABLE, buffer: IO) -> None:
        data_type: Callable = (
            # mypy doesn't seem to recognize `partial` as a function
            partial(bytes, encoding=sys.getfilesystemencoding())  # type: ignore
            if "b" in buffer.mode
            else str
        )
        if isinstance(data, (list, tuple)):
            buffer.writelines([data_type(line + "\n") for line in data])
        else:
            buffer.write(data_type(data))

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

        self._finalize_streams()

    def _finalize_streams(self) -> None:
        self._finalize_stream(self.stdout)
        self._finalize_stream(self.stderr)

    def _finalize_stream(self, stream: Optional[BUFFER]) -> None:
        if isinstance(stream, asyncio.StreamReader):
            stream.feed_eof()
        elif stream:
            stream.seek(0)

    def received_signals(self) -> Tuple[int, ...]:
        """Get a tuple of signals received by the process."""
        return tuple(self._signals)


class AsyncFakePopen(FakePopen):
    """Class to handle async processes"""

    stdout: Optional[asyncio.StreamReader]
    stderr: Optional[asyncio.StreamReader]

    async def communicate(  # type: ignore
        self, input: OPTIONAL_TEXT = None, timeout: Optional[float] = None
    ) -> Tuple[AnyType, AnyType]:
        if input:
            # streams were fed with eof, need to be reopened
            await self._reopen_streams()

            self._handle_stdin(input)

            # feed eof one more time as streams were opened
            self._finalize_streams()

        self._finalize_thread(timeout)

        return (
            await self.stdout.read() if self.stdout else None,
            await self.stderr.read() if self.stderr else None,
        )

    async def wait(self, timeout: Optional[float] = None) -> int:  # type: ignore
        return super().wait(timeout)

    def _get_empty_buffer(self, _: bool) -> asyncio.StreamReader:
        return asyncio.StreamReader()

    async def _reopen_streams(self) -> None:
        self.stdout = await self._reopen_stream(self.stdout)
        self.stderr = await self._reopen_stream(self.stderr)

    async def _reopen_stream(
        self, stream: Optional[asyncio.StreamReader]
    ) -> Optional[asyncio.StreamReader]:
        if stream:
            data = await stream.read()
            fresh_stream = self._get_empty_buffer(False)
            fresh_stream.feed_data(data)
            return fresh_stream
        return None
