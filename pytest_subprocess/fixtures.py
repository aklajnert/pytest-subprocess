from typing import Generator

import pytest

from .core import FakeProcess


@pytest.fixture
def fake_process() -> Generator[FakeProcess, None, None]:
    with FakeProcess() as process:
        yield process
