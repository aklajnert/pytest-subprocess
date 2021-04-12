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
    command = Command([Any()])
    assert check_match(command, ["test"])
    assert check_match(command, ["not_test"])
    assert check_match(command, ["something", "a", "bit", "longer"])
    assert check_match(command, ["basically", "everything", "will", "match"])

    command = Command(["test", Any()])
    assert check_match(command, ["test", "something"])
    assert check_match(command, ["test", "something_else"])
    assert check_not_match(command, ["something", "test"])
    assert check_match(command, ["test"])

    command = Command([Any(), "test"])
    assert check_match(command, ["something", "test"])
    assert check_match(command, ["something_else", "test"])
    assert check_match(command, ["test"])

    assert check_not_match(command, ["test", "something"])

    command = Command(["test", Any(), "other_test"])
    assert check_match(command, ["test", "something", "other_test"])
    assert check_match(command, ["test", "something_else", "other_test"])
    assert check_match(command, ["test", "other_test"])

    assert check_not_match(command, ["test", "something_else"])


def test_more_complex_wildcards():
    command = Command(["test", Any()])
    assert check_match(command, ["test", "with", "more", "arguments"])

    command = Command(["test", Any(), "end"])
    assert check_match(command, ["test", "blah", "end"])
    assert check_match(command, ["test", "with", "more", "arguments", "end"])
    assert check_not_match(
        command, ["test", "with", "more", "arguments", "invalid_end"]
    )


def test_any_max():
    command = Command([Any(max=1)])
    assert check_match(command, ["test"])
    assert check_match(command, ["other_test"])

    assert check_not_match(command, ["two", "arguments"])
    assert check_not_match(command, ["th", "ree", "arguments"])

    command = Command(["test", Any(max=3)])
    assert check_match(command, ["test", "max", "3", "args"])
    assert check_match(command, ["test", "can_be", "less"])
    assert check_match(command, ["test"])

    assert check_not_match(command, ["wrong", "first", "argument"])
    assert check_not_match(command, ["test", "more", "than", "3", "args"])

    command = Command(["test", Any(max=2), "end"])
    assert check_match(command, ["test", "two", "args", "end"])
    assert check_match(command, ["test", "one_arg", "end"])

    assert check_not_match(command, ["test", "oops", "three", "args", "end"])
    assert check_not_match(command, ["test", "two", "args", "wrong_end"])

    command = Command(["test", Any(max=1), "middle", Any(max=2), "end"])
    assert check_match(
        command, ["test", "one_argument", "middle", "two", "args", "end"]
    )
    assert check_match(command, ["test", "middle", "one_arg", "end"])

    assert check_not_match(
        command, ["test", "two", "args", "middle", "two", "args", "end"]
    )


def test_any_min():
    command = Command([Any(min=2)])
    assert check_match(command, ["any", "two"])
    assert check_match(command, ["or", "even", "three"])

    assert check_not_match(command, ["but_not_one"])

    command = Command(["test", Any(min=1), "end"])
    assert check_match(command, ["test", "with", "more", "arguments", "end"])
    assert check_match(command, ["test", "only_one", "end"])

    assert check_not_match(command, ["only_one", "end"])
    assert check_not_match(command, ["test", "only_one"])
    assert check_not_match(command, ["test", "end"])

    command = Command(["test", Any(min=1), "middle", Any(min=2), "end"])
    assert check_match(
        command, ["test", "one_argument", "middle", "two", "args", "end"]
    )

    assert check_not_match(command, ["test", "middle", "two", "args", "end"])
    assert check_not_match(
        command, ["test", "one_argument", "middle", "one_argument", "end"]
    )


def test_min_max_combined():
    command = Command([Any(min=2, max=4)])
    assert check_match(command, ["just", "two"])
    assert check_match(command, ["now", "three", "arguments"])
    assert check_match(command, ["up", "to", "even", "four"])

    assert check_not_match(command, ["single_argument"])
    assert check_not_match(command, ["five", "is", "little", "too", "many"])

    command = Command(["start", Any(min=1, max=1), "end"])
    assert check_match(command, ["start", "anything", "end"])

    assert check_not_match(command, ["start", "end"])
    assert check_not_match(command, ["start", "too", "many", "end"])


def test_invalid_instantiation():
    with pytest.raises(AttributeError, match="min cannot be greater than max"):
        Any(min=3, max=2)

    with pytest.raises(
        AttributeError, match=r"Cannot use `Any\(\)` one after another."
    ):
        Command([Any(), Any()])

    with pytest.raises(
        TypeError, match="Command can be only of type string, list or tuple."
    ):
        Command(dict(command="ls"))


def test_str_conversions():
    no_arguments = Any()
    assert str(no_arguments) == "Any (min=None, max=None)"

    min_max = Any(min=1, max=3)
    assert str(min_max) == "Any (min=1, max=3)"

    simple_command = Command(["ls", "-lah"])
    assert str(simple_command) == "('ls', '-lah')"

    command_with_any = Command(["ls", Any()])
    assert str(command_with_any) == "('ls', Any (min=None, max=None))"


def test_command_iter():
    """Make sure Command supports iteration"""
    command = Command(["a", "a", "a"])
    assert all(elem == "a" for elem in command)
