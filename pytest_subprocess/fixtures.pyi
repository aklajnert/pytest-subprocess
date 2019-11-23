import pytest

from .core import FakeProcess


@pytest.fixture
def fake_process() -> FakeProcess: ...
