import asyncio
import io
import os
from typing import Sequence
from typing import Union

from .utils import Any
from .utils import Command

OPTIONAL_TEXT = Union[str, bytes, None]
OPTIONAL_TEXT_OR_ITERABLE = Union[
    str,
    bytes,
    None,
    Sequence[Union[str, bytes]],
]
BUFFER = Union[io.BytesIO, io.StringIO, asyncio.StreamReader]
ARGUMENT = Union[str, Any, os.PathLike]
COMMAND = Union[Sequence[ARGUMENT], str, Command]
