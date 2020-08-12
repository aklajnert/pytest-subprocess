import pytest

from pytest_subprocess.utils import Command


@pytest.mark.parametrize("command", ("whoami", ["whoami"]))
def test_simple_command(command):
    command = Command(command)
    assert command == ("whoami",)
    assert command == ["whoami"]
    assert command == "whoami"


@pytest.mark.parametrize("command", ("test command", ("test", "command")))
def test_more_complex_command(command):
    command = Command(command)
    assert command == "test command"
    assert command != "other command"
    assert command == ("test", "command")
    assert command == ["test", "command"]
    assert command != ("other", "command")
