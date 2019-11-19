# -*- coding: utf-8 -*-
import os
import platform
import subprocess

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
            stdout="Stdout line 1\nStdout line 2\n",
            stderr="Stderr line 1\n",
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
    assert err.splitlines() == [b"Stderr line 1"]


@pytest.mark.parametrize("fake", [True, False])
def test_basic_process_merge_streams(fake_process, fake):
    """Stderr is merged into stdout."""
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py"],
            stdout="Stdout line 1\nStdout line 2\n",
            stderr="Stderr line 1\n",
        )

    process = subprocess.Popen(
        ["python", "example_script.py"],
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
            ["python", "example_script.py", "wait"],
            stdout="Stdout line 1\nStdout line 2\n",
            stderr="Stderr line 1\n",
            wait=0.5,
        )
    process = subprocess.Popen(
        ("python", "example_script.py", "wait"),
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert process.returncode is None

    with pytest.raises(subprocess.TimeoutExpired) as exc:
        process.wait(timeout=0.1)
    assert (
        str(exc.value) == "Command '('python', 'example_script.py', 'wait')' "
        "timed out after 0.1 seconds"
    )

    assert process.wait() == 0
