# -*- coding: utf-8 -*-
import os
import platform
import subprocess
import sys

import pytest

import pytest_subprocess


def setup_fake_popen(monkeypatch):
    """Set the real Popen to a dummy function that just returns input arguments."""
    monkeypatch.setattr(
        pytest_subprocess.ProcessDispatcher,
        "built_in_popen",
        lambda command, *args, **kwargs: (command, args, kwargs),
    )


@pytest.fixture(autouse=True)
def setup():
    pytest_subprocess.ProcessDispatcher.allow_unregistered(False)
    os.chdir(os.path.dirname(__file__))


def test_multiple_levels(fake_process):
    """Register fake process on different levels and check the behavior"""

    # process definition on the top level
    fake_process.register_subprocess(
        ("first_command"), stdout="first command top-level"
    )

    with fake_process.context() as fake_process2:
        # lower level, override the same command and define new one
        fake_process2.register_subprocess(
            "first_command", stdout="first command lower-level"
        )
        fake_process2.register_subprocess(
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
    fake_process = subprocess.Popen("test", shell=True)

    assert fake_process == ("test", (), {"shell": True})


def test_context(fake_process, monkeypatch):
    """Test context manager behavior."""
    setup_fake_popen(monkeypatch)

    with fake_process.context() as context:
        context.register_subprocess("test")
        subprocess.Popen("test")

        # execute twice to show that the effect doesn't wear off after single use
        subprocess.Popen("test")

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.Popen("test")

    assert str(exc.value) == "The process 'test' was not registered."


@pytest.mark.parametrize("fake", [True, False])
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

    # splitlines is required to ignore differences between LF and CRLF
    assert out.splitlines() == [b"Stdout line 1", b"Stdout line 2"]
    assert err == b""


@pytest.mark.parametrize("fake", [True, False])
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


@pytest.mark.parametrize("fake", [True, False])
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


@pytest.mark.parametrize("fake", [True, False])
def test_check_output(fake_process, fake):
    """Prove that check_output() works"""
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"], stdout="Stdout line 1\nStdout line 2",
        )
    process = subprocess.check_output(("python", "example_script.py"))

    assert process.splitlines() == [b"Stdout line 1", b"Stdout line 2"]


@pytest.mark.parametrize("fake", [True, False])
def test_check_call(fake_process, fake):
    """Prove that check_call() works"""
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


@pytest.mark.parametrize("fake", [True, False])
def test_call(fake_process, fake):
    """Prove that check_call() works"""
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"], stdout="Stdout line 1\nStdout line 2\n",
        )
    assert subprocess.call(("python", "example_script.py")) == 0


@pytest.mark.parametrize("fake", [True, False])
def test_run(fake_process, fake):
    """Prove that run() works"""
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"], stdout="Stdout line 1\nStdout line 2\n",
        )
    process = subprocess.run(("python", "example_script.py"))

    assert process
