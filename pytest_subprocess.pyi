# -*- coding: utf-8 -*-
import io
import typing

import pytest  # type: ignore

OPTIONAL_TEXT = typing.Union[str, bytes, None]

def _ensure_hashable(
    input: typing.Union[typing.List[str], typing.Tuple[str], str]
) -> typing.Union[typing.Tuple[str], str]: ...

class FakePopen:
    __command: typing.Union[typing.List[str], typing.Tuple[str], str]
    stdout: typing.Optional[io.BytesIO]
    stderr: typing.Optional[io.BytesIO]
    returncode: int
    __stdout: OPTIONAL_TEXT
    __stderr: OPTIONAL_TEXT
    def __init__(
        self,
        command: typing.Union[typing.Tuple[str], str],
        stdout: OPTIONAL_TEXT = None,
        stderr: OPTIONAL_TEXT = None,
        returncode: int = 0,
    ) -> None: ...
    def communicate(
        self, input: OPTIONAL_TEXT = ..., timeout: typing.Optional[float] = ...,
    ) -> typing.Tuple[typing.Any, typing.Any]: ...
    def configure(self, **kwargs: typing.Optional[typing.Dict]) -> None: ...
    @staticmethod
    def _prepare_buffer(
        input: typing.Union[str, bytes, None],
        io_base: typing.Optional[io.BytesIO] = None,
    ) -> io.BytesIO: ...

class ProcessNotRegisteredError(Exception): ...

class ProcessDispatcher:
    process_list: typing.List["Process"]
    built_in_popen: typing.Optional[typing.Callable]
    _allow_unregistered: bool
    @classmethod
    def register(cls, process: "Process") -> None: ...
    @classmethod
    def deregister(cls, process: "Process") -> None: ...
    @classmethod
    def dispatch(
        cls,
        command: typing.Union[typing.Tuple[str], str],
        **kwargs: typing.Optional[typing.Dict]
    ) -> FakePopen: ...
    @classmethod
    def allow_unregistered(cls, allow: bool) -> None: ...

class Process:
    processes: typing.Dict[typing.Union[str, typing.Tuple[str]], typing.Dict]
    def __init__(self) -> None: ...
    def register_subprocess(
        self,
        command: typing.Union[typing.List[str], typing.Tuple[str], str],
        stdout: OPTIONAL_TEXT = None,
        stderr: OPTIONAL_TEXT = None,
        returncode: int = 0,
    ) -> None: ...
    def __enter__(self) -> "Process": ...
    def __exit__(self, *args: typing.List, **kwargs: typing.Dict) -> None: ...
    def allow_unregistered(cls, allow: bool) -> None: ...
    @classmethod
    def context(cls) -> "Process": ...

@pytest.fixture
def fake_process() -> Process: ...
