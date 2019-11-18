# -*- coding: utf-8 -*-
import subprocess

import pytest

import pytest_subprocess


def setup_fake_popen(monkeypatch):
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
        _ = subprocess.Popen("test")
        # todo: extend this test when fake_process will be useful

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.Popen("test")

    assert str(exc.value) == "The process 'test' was not registered."
