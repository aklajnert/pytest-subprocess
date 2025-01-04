import contextlib
import getpass
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

import pytest_subprocess
from pytest_subprocess.fake_popen import FakePopen

PYTHON = sys.executable

path_or_str = pytest.mark.parametrize(
    "rtype,ptype",
    [
        pytest.param(str, str, id="str"),
        pytest.param(Path, str, id="path,str"),
        pytest.param(str, Path, id="str,path"),
        pytest.param(Path, Path, id="path"),
    ],
)


def setup_fake_popen(monkeypatch):
    """Set the real Popen to a dummy function that just returns input arguments."""
    monkeypatch.setattr(
        pytest_subprocess.process_dispatcher.ProcessDispatcher,
        "built_in_popen",
        lambda command, *args, **kwargs: (command, args, kwargs),
    )


def test_legacy_usage(fake_process):
    cmd = ["cmd"]
    fake_process.register_subprocess(cmd)

    proc = subprocess.run(cmd, check=True)

    assert proc.args == cmd
    assert isinstance(proc.args, type(cmd))


@pytest.mark.parametrize("cmd", [("cmd",), ["cmd"]])
def test_completedprocess_args(fp, cmd):
    fp.register(cmd)

    proc = subprocess.run(cmd, check=True)

    assert proc.args == cmd
    assert isinstance(proc.args, type(cmd))


@path_or_str
def test_completedprocess_args_path(fp, rtype, ptype):
    fp.register([rtype("cmd")])

    if sys.platform.startswith("win") and sys.version_info < (3, 8) and ptype is Path:
        condition = pytest.raises(TypeError)

    else:

        @contextlib.contextmanager
        def null_context():
            yield

        condition = null_context()

    with condition:
        proc = subprocess.run([ptype("cmd")], check=True)

        assert proc.args == [ptype("cmd")]
        assert isinstance(proc.args[0], ptype)


@pytest.mark.parametrize("cmd", [("cmd"), ["cmd"]])
def test_called_process_error(fp, cmd):
    fp.register(cmd, returncode=1)

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        subprocess.run(cmd, check=True)

    assert exc_info.value.cmd == cmd
    assert isinstance(exc_info.value.cmd, type(cmd))


@pytest.mark.parametrize("cmd", [("cmd"), ["cmd"]])
def test_called_process_error_with_any(fp, cmd):
    fp.register([fp.any()], returncode=1)

    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        subprocess.run(cmd, check=True)

    assert exc_info.value.cmd == cmd
    assert isinstance(exc_info.value.cmd, type(cmd))


def test_keep_last_process_error_with_any(fp):
    fp.register([fp.any()], returncode=1)
    fp.keep_last_process(True)

    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(["cmd"], check=True)

    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(["cmd2"], check=True)


def test_multiple_levels(fp):
    """Register fake process on different levels and check the behavior"""

    # process definition on the top level
    fp.register(("first_command"), stdout="first command top-level")

    with fp.context() as nested:
        # lower level, override the same command and define new one
        nested.register("first_command", stdout="first command lower-level")
        nested.register("second_command", stdout="second command lower-level")

        assert (
            subprocess.check_output("first_command")
            == ("first command lower-level").encode()
        )
        assert (
            subprocess.check_output("second_command")
            == ("second command lower-level").encode()
        )

    # first command definition shall be back at top-level definition, and the second
    # command is no longer defined so it shall raise an exception
    assert (
        subprocess.check_output("first_command") == ("first command top-level").encode()
    )
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
        subprocess.check_call("second_command")
    assert str(exc.value) == "The process 'second_command' was not registered."


def test_not_registered(fp, monkeypatch):
    """
    Scenario with attempt of running a command that is not registered.

    First two tries will raise an exception, but the last one will set
    `process.allow_unregistered(True)` which will allow to execute the process.
    """
    assert fp

    # this one will use exception from `pytest_subprocess.ProcessNotRegisteredError`
    # to make sure it still works (for backwards compatibility)
    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.Popen("test")

    assert str(exc.value) == "The process 'test' was not registered."

    with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
        subprocess.Popen(("test", "with", "args"))

    assert str(exc.value) == "The process 'test with args' was not registered."

    fp.allow_unregistered(True)
    setup_fake_popen(monkeypatch)
    result = subprocess.Popen("test", shell=True)

    assert result == ("test", (), {"shell": True})


def test_context(fp, monkeypatch):
    """Test context manager behavior."""
    setup_fake_popen(monkeypatch)

    with fp.context() as nested:
        nested.register("test")
        subprocess.Popen("test")

    with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
        subprocess.Popen("test")

    assert str(exc.value) == "The process 'test' was not registered."


@pytest.mark.parametrize("fake", [False, True])
@path_or_str
def test_basic_process(fp, fake, rtype, ptype):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [rtype(PYTHON), "example_script.py"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=None,
        )

    if sys.platform.startswith("win") and sys.version_info < (3, 8) and ptype is Path:
        condition = pytest.raises(TypeError)

    else:

        @contextlib.contextmanager
        def null_context():
            yield

        condition = null_context()

    with condition:
        process = subprocess.Popen(
            [ptype(PYTHON), "example_script.py"],
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
def test_basic_process_merge_streams(fp, fake):
    """Stderr is merged into stdout."""
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "-u", "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=["Stderr line 1"],
        )

    process = subprocess.Popen(
        [PYTHON, "-u", "example_script.py", "stderr"],
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    out, err = process.communicate()

    assert out.splitlines() == [
        b"Stdout line 1",
        b"Stdout line 2",
        b"Stderr line 1",
    ]
    assert err is None


@pytest.mark.parametrize("fake", [False, True])
def test_wait(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py", "wait", "stderr"],
            stdout="Stdout line 1\nStdout line 2",
            stderr="Stderr line 1",
            wait=0.5,
        )
    process = subprocess.Popen(
        (PYTHON, "example_script.py", "wait", "stderr"),
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert process.returncode is None

    with pytest.raises(subprocess.TimeoutExpired) as exc:
        process.wait(timeout=0.1)
    assert (
        str(exc.value).replace("\\\\", "\\")
        == f"Command '('{PYTHON}', 'example_script.py', 'wait', 'stderr')' "
        "timed out after 0.1 seconds"
    )

    assert process.wait() == 0


@pytest.mark.parametrize("fake", [False, True])
def test_check_output(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py"],
            stdout="Stdout line 1\nStdout line 2",
        )
    process = subprocess.check_output((PYTHON, "example_script.py"))

    assert process.splitlines() == [b"Stdout line 1", b"Stdout line 2"]


@pytest.mark.parametrize("fake", [False, True])
def test_check_call(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py"],
            stdout="Stdout line 1\nStdout line 2\n",
        )
        fp.register([PYTHON, "example_script.py", "non-zero"], returncode=1)
    assert subprocess.check_call((PYTHON, "example_script.py")) == 0

    # check also non-zero exit code
    with pytest.raises(subprocess.CalledProcessError) as exc:
        assert subprocess.check_call((PYTHON, "example_script.py", "non-zero")) == 1

    if sys.version_info >= (3, 6):
        assert (
            str(exc.value).replace("\\\\", "\\")
            == f"Command '('{PYTHON}', 'example_script.py', 'non-zero')' "
            "returned non-zero exit status 1."
        )


@pytest.mark.parametrize("fake", [False, True])
def test_call(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py"],
            stdout="Stdout line 1\nStdout line 2\n",
        )
    assert subprocess.call((PYTHON, "example_script.py")) == 0


@pytest.mark.parametrize("fake", [False, True])
@pytest.mark.skipif(
    sys.version_info <= (3, 5),
    reason="subprocess.run() was introduced in python3.4",
)
def test_run(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py"],
            stdout=["Stdout line 1", "Stdout line 2"],
        )
    process = subprocess.run((PYTHON, "example_script.py"), stdout=subprocess.PIPE)

    assert process.returncode == 0
    assert process.stdout == os.linesep.encode().join(
        [b"Stdout line 1", b"Stdout line 2", b""]
    )
    assert process.stderr is None


@pytest.mark.parametrize("fake", [False, True])
def test_universal_newlines(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py"],
            stdout=b"Stdout line 1\r\nStdout line 2\r\n",
        )
    process = subprocess.Popen(
        (PYTHON, "example_script.py"), universal_newlines=True, stdout=subprocess.PIPE
    )
    process.wait()

    assert process.stdout.read() == "Stdout line 1\nStdout line 2\n"


@pytest.mark.parametrize("fake", [False, True])
def test_text(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py"],
            stdout=[b"Stdout line 1", b"Stdout line 2"],
        )
    if sys.version_info < (3, 7):
        with pytest.raises(TypeError) as exc:
            subprocess.Popen(
                (PYTHON, "example_script.py"), stdout=subprocess.PIPE, text=True
            )
        assert str(exc.value) == "__init__() got an unexpected keyword argument 'text'"
    else:
        process = subprocess.Popen(
            (PYTHON, "example_script.py"), stdout=subprocess.PIPE, text=True
        )
        process.wait()

        assert process.stdout.read().splitlines() == ["Stdout line 1", "Stdout line 2"]


def test_binary(fp):
    fp.register(
        ["some-cmd"],
        stdout=bytes.fromhex("aabbcc"),
    )

    process = subprocess.Popen(["some-cmd"], stdout=subprocess.PIPE)
    process.wait()

    assert process.stdout.read() == b"\xaa\xbb\xcc"


def test_empty_stdout(fp):
    fp.register(["some-cmd"], stdout=b"")

    process = subprocess.Popen(["some-cmd"], stdout=subprocess.PIPE)
    process.wait()

    assert process.stdout.read() == b""


def test_empty_stdout_list(fp):
    fp.register(["some-cmd"], stdout=[])

    process = subprocess.Popen(["some-cmd"], stdout=subprocess.PIPE)
    process.wait()

    assert process.stdout.read() == b""


@pytest.mark.parametrize("fake", [False, True])
def test_input(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:

        def stdin_callable(input):
            return {
                "stdout": "Provide an input: Provided: {data}".format(
                    data=input.decode()
                )
            }

        fp.register(
            [PYTHON, "example_script.py", "input"],
            stdout=[b"Stdout line 1", b"Stdout line 2"],
            stdin_callable=stdin_callable,
        )

    process = subprocess.Popen(
        (PYTHON, "example_script.py", "input"),
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
def test_ambiguous_input(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register("test", occurrences=2)

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


@pytest.mark.flaky(reruns=2, condition=platform.python_implementation() == "PyPy")
@pytest.mark.parametrize("fake", [False, True])
def test_multiple_wait(fp, fake):
    """
    Wait multiple times for 0.2 seconds with process lasting for 1s.
    Third wait shall be a bit longer and will not raise an exception,
    due to exceeding the subprocess runtime.
    """
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py", "wait"],
            wait=1,
        )

    process = subprocess.Popen(
        (PYTHON, "example_script.py", "wait"),
    )
    with pytest.raises(subprocess.TimeoutExpired):
        process.wait(timeout=0.2)

    with pytest.raises(subprocess.TimeoutExpired):
        process.wait(timeout=0.2)

    process.wait(0.9)

    assert process.returncode == 0

    # one more wait shall do no harm
    process.wait(0.2)


def test_wrong_arguments(fp):
    with pytest.raises(fp.exceptions.IncorrectProcessDefinition) as exc:
        fp.register("command", wait=1, callback=lambda _: True)

    assert str(exc.value) == (
        "The 'callback' and 'wait' arguments cannot be used "
        "together. Add sleep() to your callback instead."
    )


def test_callback(fp, capsys):
    """
    This test will show a usage of the callback argument.
    The callback argument will have access to the FakePopen so it will
    change the returncode.
    One callback execution will also pass a keyword argument.
    """

    def callback(process, argument=None):
        print("from callback with argument={}".format(argument))
        process.returncode = 1

    fp.register("test", callback=callback)
    fp.register("test", callback=callback, callback_kwargs={"argument": "value"})

    assert subprocess.call("test") == 1
    assert capsys.readouterr().out == "from callback with argument=None\n"

    assert subprocess.call("test") == 1
    assert capsys.readouterr().out == "from callback with argument=value\n"


def test_mutiple_occurrences(fp):
    # register 3 occurrences of the same command at once
    fp.register("test", occurrences=3)

    process_1 = subprocess.Popen("test")
    assert process_1.returncode == 0
    process_2 = subprocess.Popen("test")
    assert process_2.returncode == 0
    assert process_2.pid == process_1.pid + 1
    process_3 = subprocess.Popen("test")
    assert process_3.returncode == 0
    assert process_3.pid == process_2.pid + 1
    # 4-th time shall raise an exception
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")

    assert str(exc.value) == "The process 'test' was not registered."


def test_different_output(fp):
    # register process with output changing each execution
    fp.register("test", stdout="first execution")
    fp.register("test", stdout="second execution")
    # the third execution will return non-zero exit code
    fp.register("test", stdout="third execution", returncode=1)

    assert subprocess.check_output("test") == b"first execution"
    assert subprocess.check_output("test") == b"second execution"
    third_process = subprocess.Popen("test", stdout=subprocess.PIPE)
    assert third_process.stdout.read() == b"third execution"
    assert third_process.returncode == 1

    # 4-th time shall raise an exception
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")

    assert str(exc.value) == "The process 'test' was not registered."

    # now, register two processes once again, but the last one will be kept forever
    fp.register("test", stdout="first execution")
    fp.register("test", stdout="second execution")
    fp.keep_last_process(True)

    # now the processes can be called forever
    assert subprocess.check_output("test") == b"first execution"
    assert subprocess.check_output("test") == b"second execution"
    assert subprocess.check_output("test") == b"second execution"
    assert subprocess.check_output("test") == b"second execution"


def test_different_output_with_context(fp):
    """
    Leaving one context shall bring back the upper contexts processes
    even if they were already consumed. This functionality is important
    to allow a broader-level fixtures that register own processes and keep
    them predictable.
    """
    fp.register("test", stdout="top-level")

    with fp.context() as nested:
        nested.register("test", stdout="nested")

        assert subprocess.check_output("test") == b"nested"
        assert subprocess.check_output("test") == b"top-level"

        with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
            subprocess.check_call("test")

        assert str(exc.value) == "The process 'test' was not registered."

    with fp.context() as nested2:
        # another nest level, the top level shall reappear
        nested2.register("test", stdout="nested2")

        assert subprocess.check_output("test") == b"nested2"
        assert subprocess.check_output("test") == b"top-level"

        with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
            subprocess.check_call("test")

        assert str(exc.value) == "The process 'test' was not registered."

    assert subprocess.check_output("test") == b"top-level"

    with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")

    assert str(exc.value) == "The process 'test' was not registered."


def test_different_output_with_context_multilevel(fp):
    """
    This is a similar test to the previous one, but here the nesting will be deeper
    """
    fp.register("test", stdout="top-level")

    with fp.context() as first_level:
        first_level.register("test", stdout="first-level")

        with fp.context() as second_level:
            second_level.register("test", stdout="second-level")

            assert subprocess.check_output("test") == b"second-level"
            assert subprocess.check_output("test") == b"first-level"
            assert subprocess.check_output("test") == b"top-level"

            with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
                subprocess.check_call("test")

        assert subprocess.check_output("test") == b"first-level"
        assert subprocess.check_output("test") == b"top-level"

        with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
            subprocess.check_call("test")

        assert str(exc.value) == "The process 'test' was not registered."

    assert subprocess.check_output("test") == b"top-level"

    with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")


def test_multiple_level_early_consuming(fp):
    """
    The top-level will be declared with two ocurrences, but the first one will
    be consumed before entering the context manager.
    """
    fp.register("test", stdout="top-level", occurrences=2)
    assert subprocess.check_output("test") == b"top-level"

    with fp.context():
        assert subprocess.check_output("test") == b"top-level"

        with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
            subprocess.check_call("test")

        assert str(exc.value) == "The process 'test' was not registered."

    assert subprocess.check_output("test") == b"top-level"

    with pytest.raises(fp.exceptions.ProcessNotRegisteredError) as exc:
        subprocess.check_call("test")

    assert str(exc.value) == "The process 'test' was not registered."


def test_keep_last_process(fp):
    """
    The ProcessNotRegisteredError will never be raised for the process that
    has been registered at least once.
    """
    fp.keep_last_process(True)
    fp.register("test", stdout="First run")
    fp.register("test", stdout="Second run")

    assert subprocess.check_output("test") == b"First run"
    assert subprocess.check_output("test") == b"Second run"
    assert subprocess.check_output("test") == b"Second run"
    assert subprocess.check_output("test") == b"Second run"


def test_git(fp):
    fp.register(["git", "branch"], stdout=["* fake_branch", "  master"])

    process = subprocess.Popen(
        ["git", "branch"], stdout=subprocess.PIPE, universal_newlines=True
    )
    out, _ = process.communicate()

    assert process.returncode == 0
    assert out == "* fake_branch\n  master\n"


def test_use_real(fp):
    fp.pass_command([PYTHON, "example_script.py"], occurrences=3)
    fp.register([PYTHON, "example_script.py"], stdout=["Fake line 1", "Fake line 2"])

    for _ in range(0, 3):
        assert (
            subprocess.check_output(
                [PYTHON, "example_script.py"], universal_newlines=True
            )
            == "Stdout line 1\nStdout line 2\n"
        )
    assert (
        subprocess.check_output([PYTHON, "example_script.py"], universal_newlines=True)
        == "Fake line 1\nFake line 2\n"
    )


@pytest.mark.skipif(os.name == "nt", reason="Skip on windows")
def test_real_process(fp):
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
        # this will fail, as "ls" command is not registered
        subprocess.call("ls")

    fp.pass_command("ls")
    # now it should be fine
    assert subprocess.call("ls") == 0

    # allow all commands to be called by real subprocess
    fp.allow_unregistered(True)
    assert subprocess.call(["ls", "-l"]) == 0


def test_context_manager(fp):
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
        # command not registered, so will raise an exception
        subprocess.check_call("test")

    with fp.context() as nested_process:
        nested_process.register("test", occurrences=3)
        # now, we can call the command 3 times without error
        assert subprocess.check_call("test") == 0
        assert subprocess.check_call("test") == 0

    # the command was called 2 times, so one occurrence left, but since the
    # context manager has been left, it is not registered anymore
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
        subprocess.check_call("test")


def test_raise_exception(fp):
    def callback_function(process):
        process.returncode = 1
        raise PermissionError("exception raised by subprocess")

    fp.register(["test"], callback=callback_function)

    with pytest.raises(PermissionError, match="exception raised by subprocess"):
        process = subprocess.Popen(["test"])
        process.wait()

    assert process.returncode == 1


def test_callback_with_arguments(fp):
    def callback_function(process, return_code):
        process.returncode = return_code

    return_code = 127

    fp.register(
        ["test"],
        callback=callback_function,
        callback_kwargs={"return_code": return_code},
    )

    process = subprocess.Popen(["test"])
    process.wait()

    assert process.returncode == return_code


def test_subprocess_pipe_without_stream_definition(fp):
    """
    From GitHub #17 - the fake_subprocess was crashing if the subprocess was called
    with stderr=subprocess.PIPE but the stderr was not defined during the process
    registration.
    """
    fp.register(
        ["test-no-stderr"],
        stdout="test",
    )
    fp.register(
        ["test-no-stdout"],
        stderr="test",
    )
    fp.register(
        ["test-no-streams"],
    )

    assert (
        subprocess.check_output(["test-no-stderr"], stderr=subprocess.STDOUT).decode()
        == "test"
    )
    assert (
        subprocess.check_output(["test-no-stdout"], stderr=subprocess.STDOUT).decode()
        == "test"
    )
    assert (
        subprocess.check_output(["test-no-streams"], stderr=subprocess.STDOUT).decode()
        == ""
    )


@pytest.mark.parametrize("command", (("test",), "test"))
def test_different_command_type(fp, command):
    """
    From GitHub #18 - registering process as ["command"] or "command" should make no
    difference, and none of those command usage attempts shall raise error.
    """
    fp.keep_last_process(True)

    fp.register(command)

    assert subprocess.check_call("test") == 0
    assert subprocess.check_call(["test"]) == 0


@pytest.mark.parametrize(
    "command", (("test", "with", "arguments"), "test with arguments")
)
def test_different_command_type_complex_command(fp, command):
    """
    Similar to previous test, but the command is more complex.
    """
    fp.keep_last_process(True)

    fp.register(command)

    assert subprocess.check_call("test with arguments") == 0
    assert subprocess.check_call(["test", "with", "arguments"]) == 0


@pytest.mark.flaky(reruns=2, condition=platform.python_implementation() == "PyPy")
def test_raise_exception_check_output(fp):
    """
    From GitHub#16 - the check_output raises the CalledProcessError exception
    when the exit code is not zero. The exception should not shadow the exception
    from the callback, if any.

    For some reason, this test is flaky on PyPy. Further investigation required.
    """

    def callback_function(_):
        raise FileNotFoundError("raised in callback")

    fp.register("regular-behavior", returncode=1)
    fp.register("custom-exception", returncode=1, callback=callback_function)

    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_output("regular-behavior")

    with pytest.raises(FileNotFoundError, match="raised in callback"):
        subprocess.check_output("custom-exception")


def test_callback_and_return_code(fp):
    """Regression - the returncode was ignored when callback_function was present."""

    def dummy_callback(_):
        pass

    def override_returncode(process):
        process.returncode = 5

    return_code = 1

    fp.register("test-dummy", returncode=return_code, callback=dummy_callback)

    process = subprocess.Popen("test-dummy")
    process.wait()

    assert process.returncode == return_code

    fp.register("test-increment", returncode=return_code, callback=override_returncode)

    process = subprocess.Popen("test-increment")
    process.wait()

    assert process.returncode == 5


@pytest.mark.skipif(
    sys.version_info <= (3, 6),
    reason="encoding and errors has been introduced in 3.6",
)
@pytest.mark.parametrize("argument", ["encoding", "errors"])
@pytest.mark.parametrize("fake", [False, True])
def test_encoding(fp, fake, argument):
    """If encoding or errors is provided, the `text=True` behavior should be enabled."""
    username = getpass.getuser()
    values = {"encoding": "utf-8", "errors": "strict"}

    fp.allow_unregistered(not fake)
    if fake:
        fp.register(["whoami"], stdout=username)

    output = subprocess.check_output(
        ["whoami"], **{argument: values.get(argument)}
    ).strip()

    assert isinstance(output, str)
    assert output.endswith(username)


@pytest.mark.parametrize("command", ["ls -lah", ["ls", "-lah"]])
def test_string_or_tuple(fp, command):
    """
    It doesn't matter how you register the command, it should work as string or list.
    """
    fp.register(command, occurrences=2)
    assert subprocess.check_call("ls -lah") == 0
    assert subprocess.check_call(["ls", "-lah"]) == 0


def test_with_wildcards(fp):
    """Use Any() with real example"""
    fp.keep_last_process(True)
    fp.register(("ls", fp.any()))

    assert subprocess.check_call("ls -lah") == 0
    assert subprocess.check_call(["ls", "-lah", "/tmp"]) == 0
    assert subprocess.check_call(["ls"]) == 0

    fp.register(["cp", fp.any(min=2)])
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
        subprocess.check_call("cp /source/dir")
    assert subprocess.check_call("cp /source/dir /tmp/random-dir") == 0

    fp.register(["cd", fp.any(max=1)])
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
        subprocess.check_call(["cd ~/ /tmp"])
    assert subprocess.check_call("cd ~/") == 0


def test_with_program(fp, monkeypatch):
    """Use Program() with real example"""
    fp.keep_last_process(True)
    fp.register((fp.program("ls"), fp.any()))

    assert subprocess.check_call("ls -lah") == 0
    assert subprocess.check_call(["/ls", "-lah", "/tmp"]) == 0
    assert subprocess.check_call(["/usr/bin/ls"]) == 0

    with monkeypatch.context():
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("PATHEXT", ".EXE")
        assert subprocess.check_call("ls.EXE -lah") == 0
        assert subprocess.check_call("ls.exe -lah") == 0

    fp.register([fp.program("cp"), fp.any()])
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
        subprocess.check_call(["other"])
    assert subprocess.check_call("cp /source/dir /tmp/random-dir") == 0

    fp.register([fp.program("cd")])
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
        subprocess.check_call(["cq"])
    assert subprocess.check_call("cd") == 0


def test_call_count(fp):
    """Check if commands are registered and counted properly"""
    fp.keep_last_process(True)
    fp.register([fp.any()])

    assert subprocess.check_call("ls -lah") == 0
    assert subprocess.check_call(["cp", "/tmp/source", "/source"]) == 0
    assert subprocess.check_call(["cp", "/source", "/destination"]) == 0
    assert subprocess.check_call(["cp", "/source", "/other/destination"]) == 0

    assert "ls -lah" in fp.calls
    assert ["cp", "/tmp/source", "/source"] in fp.calls
    assert ["cp", "/source", "/destination"] in fp.calls
    assert ["cp", "/source", "/other/destination"] in fp.calls

    assert fp.call_count("cp /tmp/source /source") == 1
    assert fp.call_count(["cp", "/source", fp.any()]) == 2
    assert fp.call_count(["cp", fp.any()]) == 3
    assert fp.call_count(["ls", "-lah"]) == 1


def test_called_process_waits_for_the_callback_to_finish(fp, tmp_path):
    output_file_path = tmp_path / "output"

    def callback(process):
        # simulate a long-running process that creates an output file at the very end
        time.sleep(1)
        output_file_path.touch()

    fp.register([fp.any()], callback=callback)
    subprocess.run(["ls", "-al"], stdin="abc")

    assert output_file_path.exists()


@pytest.mark.parametrize("method", [FakePopen.wait, FakePopen.communicate])
def test_raises_exceptions_from_callback(fp, method):
    """Make sure that both .wait() and .communicate() raise exception from callback"""

    class MyException(Exception):
        pass

    def callback(process):
        raise MyException()

    fp.register(["test"], callback=callback)

    proc = subprocess.Popen("test")
    with pytest.raises(MyException):
        method(proc)


def test_allow_unregistered_cleaning(fp):
    """
    GitHub: #46.
    The `allow_unregistered()` function should affect only the level where it was applied
    The setting shouldn't leak to a higher levels or other tests.
    """
    fp.allow_unregistered(False)

    with fp.context() as context:
        context.allow_unregistered(True)

        subprocess.run([PYTHON, "example_script.py"])
        subprocess.run([PYTHON, "example_script.py"])
        subprocess.run([PYTHON, "example_script.py"])

    with fp.context():
        with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
            subprocess.run([PYTHON, "example_script.py"])

    with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
        subprocess.run(["test"])


def test_keep_last_process_cleaning(fp):
    """
    GitHub: #46.
    The `keep_last_process()` function should affect only the level where it was applied
    The setting shouldn't leak to a higher levels or other tests.
    """
    fp.keep_last_process(False)

    with fp.context() as context:
        context.keep_last_process(True)
        context.register(["test"])

        subprocess.run(["test"])
        subprocess.run(["test"])
        subprocess.run(["test"])

    with fp.context():
        with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
            subprocess.run(["test"])

    fp.register(["test"])
    subprocess.run(["test"])
    with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
        subprocess.run(["test"])


def test_signals(fp):
    """Test signal receiving functionality"""
    fp.register("test")

    process = subprocess.Popen("test")

    process.kill()
    process.terminate()
    process.send_signal(signal.SIGSEGV)

    if sys.platform == "win32":
        expected_signals = (signal.SIGTERM, signal.SIGTERM, signal.SIGSEGV)
    else:
        expected_signals = (signal.SIGKILL, signal.SIGTERM, signal.SIGSEGV)

    assert process.received_signals() == expected_signals


def test_signal_callback(fp):
    """Test that signal callbacks work."""

    def callback(process, sig):
        if sig == signal.SIGTERM:
            process.returncode = -1

    fp.register("test", signal_callback=callback, occurrences=3)

    # no signal
    process = subprocess.Popen("test")
    process.wait()

    assert process.returncode == 0

    # other signal
    process = subprocess.Popen("test")
    process.send_signal(signal.SIGSEGV)
    process.wait()

    assert process.returncode == 0

    # sigterm
    process = subprocess.Popen("test")
    process.send_signal(signal.SIGTERM)
    process.wait()

    assert process.returncode == -1


@pytest.mark.parametrize("fake", [False, True])
@pytest.mark.parametrize("bytes", [True, False])
def test_non_piped_streams(tmpdir, fp, fake, bytes):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "-u", "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=["Stderr line 1"],
        )

    stdout_path = tmpdir.join("stdout")
    stderr_path = tmpdir.join("stderr")

    mode = "wb" if bytes else "w"

    with open(stdout_path, mode) as stdout, open(stderr_path, mode) as stderr:
        process = subprocess.Popen(
            [PYTHON, "-u", "example_script.py", "stderr"],
            stdout=stdout,
            stderr=stderr,
        )

        err, out = process.communicate()

    assert out is None
    assert err is None

    with open(stdout_path, "r") as stdout, open(stderr_path, "r") as stderr:
        out = stdout.readlines()
        err = stderr.readlines()

    assert out == ["Stdout line 1\n", "Stdout line 2\n"]
    assert err == ["Stderr line 1\n"]


@pytest.mark.parametrize("fake", [False, True])
@pytest.mark.parametrize("bytes", [True, False])
def test_non_piped_same_file(tmpdir, fp, fake, bytes):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "-u", "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr="Stderr line 1\n",
        )

    output_path = tmpdir.join("output")

    mode = "wb" if bytes else "w"

    with open(output_path, mode) as out_file:
        process = subprocess.Popen(
            [PYTHON, "-u", "example_script.py", "stderr"],
            stdout=out_file,
            stderr=out_file,
        )

        err, out = process.communicate()

    assert out is None
    assert err is None

    with open(output_path, "r") as out_file:
        output = out_file.readlines()

    assert output == ["Stdout line 1\n", "Stdout line 2\n", "Stderr line 1\n"]


def test_process_recorder(fp):
    fp.keep_last_process(True)
    recorder = fp.register(["test_script", fp.any()])
    assert recorder.calls == []
    assert recorder.call_count() == 0
    assert not recorder.was_called()

    subprocess.call(("test_script", "random_argument"))
    assert recorder.call_count() == 1
    assert recorder.was_called()
    assert recorder.was_called(("test_script", "random_argument"))
    assert not recorder.was_called(("test_script", "another_argument"))

    subprocess.Popen(["test_script", "another_argument"])
    assert recorder.call_count() == 2
    assert recorder.was_called(("test_script", "another_argument"))

    assert recorder.call_count(["test_script", "random_argument"]) == 1
    assert recorder.call_count(["test_script", "another_argument"]) == 1

    assert recorder.first_call.args == ("test_script", "random_argument")
    assert recorder.last_call.args == ["test_script", "another_argument"]

    assert all(isinstance(instance, FakePopen) for instance in recorder.calls)

    recorder.clear()

    assert not recorder.was_called()


def test_process_recorder_args(fp):
    fp.keep_last_process(True)
    recorder = fp.register(["test_script", fp.any()])

    subprocess.call(("test_script", "arg1"))
    subprocess.run(("test_script", "arg2"), env={"foo": "bar"}, cwd="/home/user")
    subprocess.Popen(
        ["test_script", "arg3"],
        env={"foo": "bar1"},
        executable="test_script",
        shell=True,
    )

    assert recorder.call_count() == 3
    assert recorder.calls[0].args == ("test_script", "arg1")
    assert recorder.calls[0].kwargs == {}
    assert recorder.calls[1].args == ("test_script", "arg2")
    assert recorder.calls[1].kwargs == {"cwd": "/home/user", "env": {"foo": "bar"}}
    assert recorder.calls[2].args == ["test_script", "arg3"]
    assert recorder.calls[2].kwargs == {
        "env": {"foo": "bar1"},
        "executable": "test_script",
        "shell": True,
    }


def test_fake_popen_is_typed(fp):
    fp.allow_unregistered(True)
    fp.register(
        [PYTHON, "example_script.py"],
        stdout=b"Stdout line 1\r\nStdout line 2\r\n",
    )

    def spawn_process() -> subprocess.Popen[str]:
        import subprocess

        return subprocess.Popen(
            (PYTHON, "example_script.py"),
            universal_newlines=True,
            stdout=subprocess.PIPE,
        )

    proc = spawn_process()
    proc.wait()

    assert proc.stdout.read() == "Stdout line 1\nStdout line 2\n"
