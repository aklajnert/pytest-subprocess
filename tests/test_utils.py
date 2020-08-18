import pytest

from pytest_subprocess.utils import Any
from pytest_subprocess.utils import Command


def check_match(command_instance, command):
    assert command_instance == command
    assert command_instance == tuple(command)
    assert command_instance == " ".join(command)
    return True


def check_not_match(command_instance, command):
    assert command_instance != command
    assert command_instance != tuple(command)
    assert command_instance != " ".join(command)
    return True


@pytest.mark.parametrize("command", ("whoami", ["whoami"]))
def test_simple_command(command):
    command = Command(command)
    assert check_match(command, ["whoami"])


@pytest.mark.parametrize("command", ("test command", ("test", "command")))
def test_more_complex_command(command):
    command = Command(command)
    assert check_match(command, ["test", "command"])
    assert check_not_match(command, ["other", "command"])


def test_simple_wildcards():
    command = Command(["test", Any()])
    assert check_match(command, ["test", "something"])
    assert check_match(command, ["test", "something_else"])
    assert check_not_match(command, ["something", "test"])

    command = Command([Any(), "test"])
    assert check_match(command, ["something", "test"])
    assert check_match(command, ["something_else", "test"])
    assert check_not_match(command, ["test", "something"])

    command = Command(["test", Any(), "other_test"])
    assert check_match(command, ["test", "something", "other_test"])
    assert check_match(command, ["test", "something_else", "other_test"])

    # the two tests below are commented-out as the current implementation doesn't
    # support matching for non-exact lists
    # assert check_not_match(command, ["test", "something_else"])
    # assert check_not_match(command, ["test", "other_test"])
