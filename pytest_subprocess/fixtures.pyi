import pytest  # type: ignore

from .core import FakeProcess


@pytest.fixture
def fake_process() -> FakeProcess: ...
