# -*- coding: utf-8 -*-
import getpass
import os
import platform
import subprocess
import sys

import pytest

import pytest_subprocess


def setup_fake_popen(monkeypatch):
    """Set the real Popen to a dummy function that just returns input arguments."""
    monkeypatch.setattr(
        pytest_subprocess.core.ProcessDispatcher,
        "built_in_popen",
        lambda command, *args, **kwargs: (command, args, kwargs),
    )


@pytest.fixture(autouse=True)
def setup():
    pytest_subprocess.core.ProcessDispatcher.allow_unregistered(False)
    pytest_subprocess.core.ProcessDispatcher.keep_last_process(False)
    os.chdir(os.path.dirname(__file__))


def test_multiple_levels(fake_process):
    """Register fake process on different levels and check the behavior"""

    # process definition on the top level
    fake_process.register_subprocess(
        ("first_command"), stdout="first command top-level"
    )

    with fake_process.context() as nested:
        # lower level, override the same command and define new one
        nested.register_subprocess("first_command", stdout="first command lower-level")
        nested.register_subprocess(
            "second_command", stdout="second command lower-level"
        )

        assert (
            subprocess.check_output("first_command")
            == ("first command lower-level" + os.linesep).encode()
        )
        assert (
            subprocess.check_output("second_command")
            == ("second command lower-level" + os.linesep).encode()
        )

    # first command definition shall be back at top-level definition, and the second
    # command is no longer defined so it shall raise an exception
    assert (
        subprocess.check_output("first_command")
        == ("first command top-level" + os.linesep).encode()
    )
    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.check_call("second_command")
    assert str(exc.value) == "The process 'second_command' was not registered."


def test_not_registered(fake_process, monkeypatch):
    """
    Scenario with attempt of running a command that is not registered.

    First two tries will raise an exception, but the last one will set
    `process.allow_unregistered(True)` which will allow to execute the process.
    """
    assert fake_process

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.Popen("test")

    assert str(exc.value) == "The process 'test' was not registered."

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.Popen(("test", "with", "args"))

    assert str(exc.value) == "The process 'test with args' was not registered."

    fake_process.allow_unregistered(True)
    setup_fake_popen(monkeypatch)
    result = subprocess.Popen("test", shell=True)

    assert result == ("test", (), {"shell": True})


def test_context(fake_process, monkeypatch):
    """Test context manager behavior."""
    setup_fake_popen(monkeypatch)

    with fake_process.context() as nested:
        nested.register_subprocess("test")
        subprocess.Popen("test")

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.Popen("test")

    assert str(exc.value) == "The process 'test' was not registered."


@pytest.mark.parametrize("fake", [False, True])
def test_basic_process(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=None,
        )

    process = subprocess.Popen(
        ["python", "example_script.py"],
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()

    assert process.poll() == 0
    assert process.returncode == 0
    assert process.pid > 0

    # splitlines is required to ignore differences between LF and CRLF
    assert out.splitlines() == [b"Stdout line 1", b"Stdout line 2"]
    assert err == b""


@pytest.mark.parametrize("fake", [False, True])
def test_basic_process_merge_streams(fake_process, fake):
    """Stderr is merged into stdout."""
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py", "stderr"],
            stdout="Stdout line 1\nStdout line 2",
            stderr="Stderr line 1",
        )

    process = subprocess.Popen(
        ["python", "example_script.py", "stderr"],
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, err = process.communicate()

    if fake or platform.python_implementation() != "CPython":
        # if the streams are merged form two different sources, there's no way to
        # preserve the original order, stdout content will be first - followed by stderr
        # this seems to be a default behavior on pypy
        assert out.splitlines() == [
            b"Stdout line 1",
            b"Stdout line 2",
            b"Stderr line 1",
        ]
    elif platform.system().lower() == "linux":
        # CPython on linux seems to put the stderr first
        assert out.splitlines() == [
            b"Stderr line 1",
            b"Stdout line 1",
            b"Stdout line 2",
        ]
    else:
        assert out.splitlines() == [
            b"Stdout line 1",
            b"Stderr line 1",
            b"Stdout line 2",
        ]
    assert err is None


@pytest.mark.parametrize("fake", [False, True])
def test_wait(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py", "wait", "stderr"],
            stdout="Stdout line 1\nStdout line 2",
            stderr="Stderr line 1",
            wait=0.5,
        )
    process = subprocess.Popen(
        ("python", "example_script.py", "wait", "stderr"),
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert process.returncode is None

    with pytest.raises(subprocess.TimeoutExpired) as exc:
        process.wait(timeout=0.1)
    assert (
        str(exc.value) == "Command '('python', 'example_script.py', 'wait', 'stderr')' "
        "timed out after 0.1 seconds"
    )

    assert process.wait() == 0


@pytest.mark.parametrize("fake", [False, True])
def test_check_output(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"], stdout="Stdout line 1\nStdout line 2",
        )
    process = subprocess.check_output(("python", "example_script.py"))

    assert process.splitlines() == [b"Stdout line 1", b"Stdout line 2"]


@pytest.mark.parametrize("fake", [False, True])
def test_check_call(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"], stdout="Stdout line 1\nStdout line 2\n",
        )
        fake_process.register_subprocess(
            ["python", "example_script.py", "non-zero"], returncode=1
        )
    assert subprocess.check_call(("python", "example_script.py")) == 0

    # check also non-zero exit code
    with pytest.raises(subprocess.CalledProcessError) as exc:
        assert subprocess.check_call(("python", "example_script.py", "non-zero")) == 1

    if sys.version_info >= (3, 6):
        assert (
            str(exc.value) == "Command '('python', 'example_script.py', 'non-zero')' "
            "returned non-zero exit status 1."
        )


@pytest.mark.parametrize("fake", [False, True])
def test_call(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"], stdout="Stdout line 1\nStdout line 2\n",
        )
    assert subprocess.call(("python", "example_script.py")) == 0


@pytest.mark.parametrize("fake", [False, True])
@pytest.mark.skipif(
    sys.version_info <= (3, 5), reason="subprocess.run() was introduced in python3.4",
)
def test_run(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"], stdout=["Stdout line 1", "Stdout line 2"],
        )
    process = subprocess.run(("python", "example_script.py"), stdout=subprocess.PIPE)

    assert process.returncode == 0
    assert process.stdout == os.linesep.encode().join(
        [b"Stdout line 1", b"Stdout line 2", b""]
    )
    assert process.stderr is None


@pytest.mark.parametrize("fake", [False, True])
def test_universal_newlines(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"], stdout=b"Stdout line 1\r\nStdout line 2",
        )
    process = subprocess.Popen(
        ("python", "example_script.py"), universal_newlines=True, stdout=subprocess.PIPE
    )
    process.wait()

    assert process.stdout.read() == "Stdout line 1\nStdout line 2\n"


@pytest.mark.parametrize("fake", [False, True])
def test_text(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"],
            stdout=[b"Stdout line 1", b"Stdout line 2"],
        )
    if sys.version_info < (3, 7):
        with pytest.raises(TypeError) as exc:
            subprocess.Popen(
                ("python", "example_script.py"), stdout=subprocess.PIPE, text=True
            )
        assert str(exc.value) == "__init__() got an unexpected keyword argument 'text'"
    else:
        process = subprocess.Popen(
            ("python", "example_script.py"), stdout=subprocess.PIPE, text=True
        )
        process.wait()

        assert process.stdout.read().splitlines() == ["Stdout line 1", "Stdout line 2"]


@pytest.mark.parametrize("fake", [False, True])
def test_input(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:

        def stdin_callable(input):
            return {
                "stdout": "Provide an input: Provided: {data}".format(
                    data=input.decode()
                )
            }

        fake_process.register_subprocess(
            ["python", "example_script.py", "input"],
            stdout=[b"Stdout line 1", b"Stdout line 2"],
            stdin_callable=stdin_callable,
        )

    process = subprocess.Popen(
        ("python", "example_script.py", "input"),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    out, err = process.communicate(input=b"test")

    assert out.splitlines() == [
        b"Stdout line 1",
        b"Stdout line 2",
        b"Provide an input: Provided: test",
    ]
    assert err is None


@pytest.mark.skipif(
    sys.version_info < (3, 7),
    reason="No need to test since 'text' is available since 3.7",
)
@pytest.mark.parametrize("fake", [False, True])
def test_ambiguous_input(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess("test", occurrences=2)

    with pytest.raises(subprocess.SubprocessError) as exc:
        subprocess.run("test", universal_newlines=False, text=True)

    assert str(exc.value) == (
        "Cannot disambiguate when both text "
        "and universal_newlines are supplied but "
        "different. Pass one or the other."
    )

    with pytest.raises(subprocess.SubprocessError) as exc:
        subprocess.run("test", universal_newlines=True, text=False)

    assert str(exc.value) == (
        "Cannot disambiguate when both text "
        "and universal_newlines are supplied but "
        "different. Pass one or the other."
    )


@pytest.mark.parametrize("fake", [False, True])
def test_multiple_wait(fake_process, fake):
    """
    Wait multiple times for 0.2 seconds with process lasting for 0.5.
    Third wait shall not raise an exception.
    """
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py", "wait"], wait=0.5,
        )

    process = subprocess.Popen(("python", "example_script.py", "wait"),)
    with pytest.raises(subprocess.TimeoutExpired):
        process.wait(timeout=0.2)

    with pytest.raises(subprocess.TimeoutExpired):
        process.wait(timeout=0.2)

    process.wait(0.2)

    assert process.returncode == 0

    # one more wait shall do no harm
    process.wait(0.2)


def test_wrong_arguments(fake_process):
    with pytest.raises(pytest_subprocess.IncorrectProcessDefinition) as exc:
        fake_process.register_subprocess("command", wait=1, callback=lambda _: True)

    assert str(exc.value) == (
        "The 'callback' and 'wait' arguments cannot be used "
        "together. Add sleep() to your callback instead."
    )


def test_callback(fake_process, capsys):
    """
    This test will show a usage of the callback argument.
    The callback argument will have access to the FakePopen so it will
    change the returncode.
    One callback execution will also pass a keyword argument.
    """

    def callback(process, argument=None):
        print("from callback with argument={}".format(argument))
        process.returncode = 1

    fake_process.register_subprocess("test", callback=callback)
    fake_process.register_subprocess(
        "test", callback=callback, callback_kwargs={"argument": "value"}
    )

    assert subprocess.call("test") == 1
    assert capsys.readouterr().out == "from callback with argument=None\n"

    assert subprocess.call("test") == 1
    assert capsys.readouterr().out == "from callback with argument=value\n"


def test_mutiple_occurrences(fake_process):
    # register 3 occurrences of the same command at once
    fake_process.register_subprocess("test", occurrences=3)

    process_1 = subprocess.Popen("test")
    assert process_1.returncode == 0
    process_2 = subprocess.Popen("test")
    assert process_2.returncode == 0
    assert process_2.pid == process_1.pid + 1
    process_3 = subprocess.Popen("test")
    assert process_3.returncode == 0
    assert process_3.pid == process_2.pid + 1
    # 4-th time shall raise an exception
    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")

    assert str(exc.value) == "The process 'test' was not registered."


def test_different_output(fake_process):
    # register process with output changing each execution
    fake_process.register_subprocess("test", stdout="first execution")
    fake_process.register_subprocess("test", stdout="second execution")
    # the third execution will return non-zero exit code
    fake_process.register_subprocess("test", stdout="third execution", returncode=1)

    assert subprocess.check_output("test") == b"first execution" + os.linesep.encode()
    assert subprocess.check_output("test") == b"second execution" + os.linesep.encode()
    third_process = subprocess.Popen("test", stdout=subprocess.PIPE)
    assert third_process.stdout.read() == b"third execution" + os.linesep.encode()
    assert third_process.returncode == 1

    # 4-th time shall raise an exception
    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")

    assert str(exc.value) == "The process 'test' was not registered."

    # now, register two processes once again, but the last one will be kept forever
    fake_process.register_subprocess("test", stdout="first execution")
    fake_process.register_subprocess("test", stdout="second execution")
    fake_process.keep_last_process(True)

    # now the processes can be called forever
    assert subprocess.check_output("test") == b"first execution" + os.linesep.encode()
    assert subprocess.check_output("test") == b"second execution" + os.linesep.encode()
    assert subprocess.check_output("test") == b"second execution" + os.linesep.encode()
    assert subprocess.check_output("test") == b"second execution" + os.linesep.encode()


def test_different_output_with_context(fake_process):
    """
    Leaving one context shall bring back the upper contexts processes
    even if they were already consumed. This functionality is important
    to allow a broader-level fixtures that register own processes and keep
    them predictable.
    """
    fake_process.register_subprocess("test", stdout="top-level")

    with fake_process.context() as nested:
        nested.register_subprocess("test", stdout="nested")

        assert subprocess.check_output("test") == b"nested" + os.linesep.encode()
        assert subprocess.check_output("test") == b"top-level" + os.linesep.encode()

        with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
            subprocess.check_call("test")

        assert str(exc.value) == "The process 'test' was not registered."

    with fake_process.context() as nested2:
        # another nest level, the top level shall reappear
        nested2.register_subprocess("test", stdout="nested2")

        assert subprocess.check_output("test") == b"nested2" + os.linesep.encode()
        assert subprocess.check_output("test") == b"top-level" + os.linesep.encode()

        with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
            subprocess.check_call("test")

        assert str(exc.value) == "The process 'test' was not registered."

    assert subprocess.check_output("test") == b"top-level" + os.linesep.encode()

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")

    assert str(exc.value) == "The process 'test' was not registered."


def test_different_output_with_context_multilevel(fake_process):
    """
    This is a similar test to the previous one, but here the nesting will be deeper
    """
    fake_process.register_subprocess("test", stdout="top-level")

    with fake_process.context() as first_level:
        first_level.register_subprocess("test", stdout="first-level")

        with fake_process.context() as second_level:
            second_level.register_subprocess("test", stdout="second-level")

            assert (
                subprocess.check_output("test") == b"second-level" + os.linesep.encode()
            )
            assert (
                subprocess.check_output("test") == b"first-level" + os.linesep.encode()
            )
            assert subprocess.check_output("test") == b"top-level" + os.linesep.encode()

            with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
                subprocess.check_call("test")

        assert subprocess.check_output("test") == b"first-level" + os.linesep.encode()
        assert subprocess.check_output("test") == b"top-level" + os.linesep.encode()

        with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
            subprocess.check_call("test")

        assert str(exc.value) == "The process 'test' was not registered."

    assert subprocess.check_output("test") == b"top-level" + os.linesep.encode()

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")


def test_multiple_level_early_consuming(fake_process):
    """
    The top-level will be declared with two ocurrences, but the first one will
    be consumed before entering the context manager.
    """
    fake_process.register_subprocess("test", stdout="top-level", occurrences=2)
    assert subprocess.check_output("test") == b"top-level" + os.linesep.encode()

    with fake_process.context():
        assert subprocess.check_output("test") == b"top-level" + os.linesep.encode()

        with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
            subprocess.check_call("test")

        assert str(exc.value) == "The process 'test' was not registered."

    assert subprocess.check_output("test") == b"top-level" + os.linesep.encode()

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")

    assert str(exc.value) == "The process 'test' was not registered."


def test_keep_last_process(fake_process):
    """
    The ProcessNotRegisteredError will never be raised for the process that
    has been registered at least once.
    """
    fake_process.keep_last_process(True)
    fake_process.register_subprocess("test", stdout="First run")
    fake_process.register_subprocess("test", stdout="Second run")

    assert subprocess.check_output("test") == b"First run" + os.linesep.encode()
    assert subprocess.check_output("test") == b"Second run" + os.linesep.encode()
    assert subprocess.check_output("test") == b"Second run" + os.linesep.encode()
    assert subprocess.check_output("test") == b"Second run" + os.linesep.encode()


def test_git(fake_process):
    fake_process.register_subprocess(
        ["git", "branch"], stdout=["* fake_branch", "  master"]
    )

    process = subprocess.Popen(
        ["git", "branch"], stdout=subprocess.PIPE, universal_newlines=True
    )
    out, _ = process.communicate()

    assert process.returncode == 0
    assert out == "* fake_branch\n  master\n"


def test_use_real(fake_process):
    fake_process.pass_command(["python", "example_script.py"], occurrences=3)
    fake_process.register_subprocess(
        ["python", "example_script.py"], stdout="Fake line 1\nFake line 2"
    )

    for _ in range(0, 3):
        assert (
            subprocess.check_output(
                ["python", "example_script.py"], universal_newlines=True
            )
            == "Stdout line 1\nStdout line 2\n"
        )
    assert (
        subprocess.check_output(
            ["python", "example_script.py"], universal_newlines=True
        )
        == "Fake line 1\nFake line 2\n"
    )


@pytest.mark.skipif(os.name == "nt", reason="Skip on windows")
def test_real_process(fake_process):
    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
        # this will fail, as "ls" command is not registered
        subprocess.call("ls")

    fake_process.pass_command("ls")
    # now it should be fine
    assert subprocess.call("ls") == 0

    # allow all commands to be called by real subprocess
    fake_process.allow_unregistered(True)
    assert subprocess.call(["ls", "-l"]) == 0


def test_context_manager(fake_process):
    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
        # command not registered, so will raise an exception
        subprocess.check_call("test")

    with fake_process.context() as nested_process:
        nested_process.register_subprocess("test", occurrences=3)
        # now, we can call the command 3 times without error
        assert subprocess.check_call("test") == 0
        assert subprocess.check_call("test") == 0

    # the command was called 2 times, so one occurrence left, but since the
    # context manager has been left, it is not registered anymore
    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
        subprocess.check_call("test")


def test_raise_exception(fake_process):
    def callback_function(process):
        process.returncode = 1
        raise PermissionError("exception raised by subprocess")

    fake_process.register_subprocess(["test"], callback=callback_function)

    with pytest.raises(PermissionError, match="exception raised by subprocess"):
        process = subprocess.Popen(["test"])
        process.wait()

    assert process.returncode == 1


def test_callback_with_arguments(fake_process):
    def callback_function(process, return_code):
        process.returncode = return_code

    return_code = 127

    fake_process.register_subprocess(
        ["test"],
        callback=callback_function,
        callback_kwargs={"return_code": return_code},
    )

    process = subprocess.Popen(["test"])
    process.wait()

    assert process.returncode == return_code


def test_subprocess_pipe_without_stream_definition(fake_process):
    """
    From GitHub #17 - the fake_subprocess was crashing if the subprocess was called
    with stderr=subprocess.PIPE but the stderr was not defined during the process
    registration.
    """
    fake_process.register_subprocess(
        ["test-no-stderr"], stdout="test",
    )
    fake_process.register_subprocess(
        ["test-no-stdout"], stderr="test",
    )
    fake_process.register_subprocess(["test-no-streams"],)

    assert (
        subprocess.check_output(["test-no-stderr"], stderr=subprocess.STDOUT).decode()
        == "test" + os.linesep
    )
    assert (
        subprocess.check_output(["test-no-stdout"], stderr=subprocess.STDOUT).decode()
        == "test" + os.linesep
    )
    assert (
        subprocess.check_output(["test-no-streams"], stderr=subprocess.STDOUT).decode()
        == ""
    )


@pytest.mark.parametrize("command", (("test",), "test"))
def test_different_command_type(fake_process, command):
    """
    From GitHub #18 - registering process as ["command"] or "command" should make no
    difference, and none of those command usage attempts shall raise error.
    """
    fake_process.keep_last_process(True)

    fake_process.register_subprocess(command)

    assert subprocess.check_call("test") == 0
    assert subprocess.check_call(["test"]) == 0


@pytest.mark.parametrize(
    "command", (("test", "with", "arguments"), "test with arguments")
)
def test_different_command_type_complex_command(fake_process, command):
    """
    Similar to previous test, but the command is more complex.
    """
    fake_process.keep_last_process(True)

    fake_process.register_subprocess(command)

    assert subprocess.check_call("test with arguments") == 0
    assert subprocess.check_call(["test", "with", "arguments"]) == 0


def test_raise_exception_check_output(fake_process):
    """
    From GitHub#16 - the check_output raises the CalledProcessError exception
    when the exit code is not zero. The exception should not shadow the exception
    from the callback, if any.
    """

    def callback_function(_):
        raise FileNotFoundError("raised in callback")

    fake_process.register_subprocess("regular-behavior", returncode=1)
    fake_process.register_subprocess(
        "custom-exception", returncode=1, callback=callback_function
    )

    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_output("regular-behavior")

    with pytest.raises(FileNotFoundError, match="raised in callback"):
        subprocess.check_output("custom-exception")


def test_callback_and_return_code(fake_process):
    """Regression - the returncode was ignored when callback_function was present."""

    def dummy_callback(_):
        pass

    def override_returncode(process):
        process.returncode = 5

    return_code = 1

    fake_process.register_subprocess(
        "test-dummy", returncode=return_code, callback=dummy_callback
    )

    process = subprocess.Popen("test-dummy")
    process.wait()

    assert process.returncode == return_code

    fake_process.register_subprocess(
        "test-increment", returncode=return_code, callback=override_returncode
    )

    process = subprocess.Popen("test-increment")
    process.wait()

    assert process.returncode == 5


@pytest.mark.skipif(
    sys.version_info <= (3, 6), reason="encoding and errors has been introduced in 3.6",
)
@pytest.mark.parametrize("argument", ["encoding", "errors"])
@pytest.mark.parametrize("fake", [False, True])
def test_encoding(fake_process, fake, argument):
    """If encoding or errors is provided, the `text=True` behavior should be enabled."""
    username = getpass.getuser()
    values = {"encoding": "utf-8", "errors": "strict"}

    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(["whoami"], stdout=username)

    output = subprocess.check_output(
        ["whoami"], **{argument: values.get(argument)}
    ).strip()

    assert isinstance(output, str)
    assert output.endswith(username)


@pytest.mark.parametrize("command", ["ls -lah", ["ls", "-lah"]])
def test_string_or_tuple(fake_process, command):
    """
    It doesn't matter how you register the command, it should work as string or list.
    """
    fake_process.register_subprocess(command, occurrences=2)
    assert subprocess.check_call("ls -lah") == 0
    assert subprocess.check_call(["ls", "-lah"]) == 0


def test_with_wildcards(fake_process):
    """Use Any() with real example"""
    fake_process.keep_last_process(True)
    fake_process.register_subprocess(("ls", fake_process.any()))

    assert subprocess.check_call("ls -lah") == 0
    assert subprocess.check_call(["ls", "-lah", "/tmp"]) == 0
    assert subprocess.check_call(["ls"]) == 0

    fake_process.register_subprocess(["cp", fake_process.any(min=2)])
    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
        subprocess.check_call("cp /source/dir")
    assert subprocess.check_call("cp /source/dir /tmp/random-dir") == 0

    fake_process.register_subprocess(["cd", fake_process.any(max=1)])
    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
        subprocess.check_call(["cd ~/ /tmp"])
    assert subprocess.check_call("cd ~/") == 0


def test_call_count(fake_process):
    """Check if commands are registered and counted properly"""
    fake_process.keep_last_process(True)
    fake_process.register_subprocess([fake_process.any()])

    assert subprocess.check_call("ls -lah") == 0
    assert subprocess.check_call(["cp", "/tmp/source", "/source"]) == 0
    assert subprocess.check_call(["cp", "/source", "/destination"]) == 0
    assert subprocess.check_call(["cp", "/source", "/other/destination"]) == 0

    assert "ls -lah" in fake_process.calls
    assert ["cp", "/tmp/source", "/source"] in fake_process.calls
    assert ["cp", "/source", "/destination"] in fake_process.calls
    assert ["cp", "/source", "/other/destination"] in fake_process.calls

    assert fake_process.call_count("cp /tmp/source /source") == 1
    assert fake_process.call_count(["cp", "/source", fake_process.any()]) == 2
    assert fake_process.call_count(["cp", fake_process.any()]) == 3
    assert fake_process.call_count(["ls", "-lah"]) == 1
