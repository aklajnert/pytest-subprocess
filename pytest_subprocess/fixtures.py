import pytest

from .core import FakeProcess


@pytest.fixture
def fake_process():
    with FakeProcess() as process:
        yield process
