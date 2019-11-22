# -*- coding: utf-8 -*-
import io
import threading
import typing

import pytest  # type: ignore

OPTIONAL_TEXT = typing.Union[str, bytes, None]
OPTIONAL_TEXT_OR_ITERABLE = typing.Union[
    str,
    bytes,
    None,
    typing.List[typing.Union[str, bytes]],
    typing.Tuple[typing.Union[str, bytes], ...],
]
BUFFER = typing.Union[None, io.BytesIO, io.StringIO]

def _ensure_hashable(
    input: typing.Union[typing.List[str], typing.Tuple[str, ...], str]
) -> typing.Union[typing.Tuple[str, ...], str]: ...

class FakePopen:
    args: typing.Union[typing.List[str], typing.Tuple[str, ...], str]
    stdout: BUFFER
    stderr: BUFFER
    returncode: typing.Optional[int]
    text_mode: bool
    __stdout: OPTIONAL_TEXT_OR_ITERABLE
    __stderr: OPTIONAL_TEXT_OR_ITERABLE
    __returncode: typing.Optional[int]
    __wait: typing.Optional[float]
    __callback: typing.Optional[typing.Optional[typing.Callable]]
    __thread: typing.Optional[threading.Thread]
    def __init__(
        self,
        command: typing.Union[typing.Tuple[str, ...], str],
        stdout: OPTIONAL_TEXT_OR_ITERABLE = None,
        stderr: OPTIONAL_TEXT_OR_ITERABLE = None,
        returncode: int = 0,
        wait: typing.Optional[float] = None,
        callback: typing.Optional[typing.Callable] = None,
        **_: typing.Dict[str, typing.Any]
    ) -> None: ...
    def __enter__(self) -> "FakePopen": ...
    def __exit__(self, *args: typing.List, **kwargs: typing.Dict) -> None: ...
    def communicate(
        self, input: OPTIONAL_TEXT = ..., timeout: typing.Optional[float] = ...,
    ) -> typing.Tuple[typing.Any, typing.Any]: ...
    def poll(self) -> None: ...
    def wait(self, timeout: typing.Optional[float] = None) -> int: ...
    def configure(self, **kwargs: typing.Optional[typing.Dict]) -> None: ...
    def _prepare_buffer(
        self,
        input: typing.Union[str, bytes, None],
        io_base: BUFFER = None,
    ) -> io.BytesIO: ...
    def _convert(self, input: typing.Union[str, bytes]) -> typing.Union[str, bytes]: ...
    def _wait(self, wait_period: float) -> None: ...
    def run_thread(self) -> None: ...
    def _finish_process(self) -> None: ...

class ProcessNotRegisteredError(Exception): ...

class ProcessDispatcher:
    process_list: typing.List["Process"]
    built_in_popen: typing.Optional[typing.Optional[typing.Callable]]
    _allow_unregistered: bool
    _cache: typing.Dict[Process, typing.Dict[Process, typing.Any]]
    _keep_last_process: bool
    @classmethod
    def register(cls, process: "Process") -> None: ...
    @classmethod
    def deregister(cls, process: "Process") -> None: ...
    @classmethod
    def dispatch(
        cls,
        command: typing.Union[typing.Tuple[str, ...], str],
        **kwargs: typing.Optional[typing.Dict]
    ) -> FakePopen: ...
    @classmethod
    def allow_unregistered(cls, allow: bool) -> None: ...
    @classmethod
    def keep_last_process(cls, leave: bool) -> None: ...

class IncorrectProcessDefinition(Exception): ...

class Process:
    processes: typing.DefaultDict[str, typing.Deque[typing.Dict]]
    def __init__(self) -> None: ...
    def register_subprocess(
        self,
        command: typing.Union[typing.List[str], typing.Tuple[str, ...], str],
        stdout: OPTIONAL_TEXT_OR_ITERABLE = None,
        stderr: OPTIONAL_TEXT_OR_ITERABLE = None,
        returncode: int = 0,
        wait: typing.Optional[float] = None,
        callback: typing.Optional[typing.Callable] = None,
        occurrences: int = 1,
    ) -> None: ...
    def __enter__(self) -> "Process": ...
    def __exit__(self, *args: typing.List, **kwargs: typing.Dict) -> None: ...
    @classmethod
    def allow_unregistered(cls, allow: bool) -> None: ...
    @classmethod
    def keep_last_process(cls, leave: bool) -> None: ...
    @classmethod
    def context(cls) -> "Process": ...

@pytest.fixture
def fake_process() -> Process: ...
