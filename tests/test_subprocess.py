# -*- coding: utf-8 -*-
import subprocess

import pytest

import pytest_subprocess


def test_not_registered(process, monkeypatch):
    assert process

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.Popen("test")

    assert str(exc.value) == "The process 'test' was not registered."

    with pytest.raises(pytest_subprocess.ProcessNotRegisteredError) as exc:
        subprocess.Popen(("test", "with", "args"))

    assert str(exc.value) == "The process 'test with args' was not registered."

    process.allow_unregistered(True)
    monkeypatch.setattr(
        pytest_subprocess.ProcessDispatcher,
        "built_in_popen",
        lambda command, *args, **kwargs: (command, args, kwargs),
    )
    process = subprocess.Popen("test", shell=True)

    assert process == ("test", (), {"shell": True})
