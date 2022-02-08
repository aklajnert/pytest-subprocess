from typing import Generator

import pytest

from . import FakeProcess


@pytest.fixture
def fp() -> Generator[FakeProcess, None, None]:
    """Fake subprocess calls."""
    with FakeProcess() as process:
        yield process


fake_process = fp
