"""Additional target for mypy type checking"""
from pytest_subprocess import FakeProcess


def test_typing() -> None:
    fp = FakeProcess()
    cmd = ["ls", "-l"]
    output = ["some", "lines", "of", "output"]
    fp.register_subprocess(cmd, stdout=output)
