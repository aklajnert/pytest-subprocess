import asyncio
import os
import sys
import time

import pytest


@pytest.fixture(autouse=True)
def event_loop(request):
    policy = asyncio.get_event_loop_policy()
    if sys.platform == "win32":
        if request.node.name.startswith("test_invalid_event_loop"):
            loop = asyncio.SelectorEventLoop()
        else:
            loop = asyncio.ProactorEventLoop()
    else:
        loop = policy.get_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["shell", "exec"])
async def test_basic_usage(fake_process, mode):
    shell = mode == "shell"
    fake_process.register_subprocess(
        ["some-command-that-is-definitely-unavailable"], returncode=500
    )
    method = (
        asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
    )
    process = await method("some-command-that-is-definitely-unavailable")
    returncode = await process.wait()

    assert process.returncode == returncode
    assert process.returncode == 500


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [True, False])
async def test_with_arguments_shell(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=["Stderr line 1"],
        )

    process = await asyncio.create_subprocess_shell(
        "python example_script.py stderr",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate()

    assert err == os.linesep.encode().join([b"Stderr line 1", b""])
    assert out == os.linesep.encode().join([b"Stdout line 1", b"Stdout line 2", b""])
    assert process.returncode == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [True, False])
async def test_with_arguments_exec(fake_process, fake):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=["Stderr line 1"],
        )

    process = await asyncio.create_subprocess_exec(
        "python",
        "example_script.py",
        "stderr",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate()

    assert err == os.linesep.encode().join([b"Stderr line 1", b""])
    assert out == os.linesep.encode().join([b"Stdout line 1", b"Stdout line 2", b""])
    assert process.returncode == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [True, False])
@pytest.mark.parametrize("mode", ["shell", "exec"])
async def test_incorrect_call(fake_process, fake, mode):
    """Asyncio doesn't support command as a list"""
    shell = mode == "shell"
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(["test"])

    method = (
        asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
    )

    name = "cmd" if shell else "program"
    with pytest.raises(ValueError, match=f"{name} must be a string"):
        await method(["test"])


@pytest.mark.asyncio
@pytest.mark.skipif('sys.platform!="win32"')
@pytest.mark.parametrize("fake", [True, False])
@pytest.mark.parametrize("mode", ["shell", "exec"])
async def test_invalid_event_loop(fake_process, fake, mode):
    """
    The event_loop is changed by the `event_loop` fixture based on
    the test name (hack).
    """
    shell = mode == "shell"
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(["python", "example_script.py"])

    with pytest.raises(NotImplementedError):
        if shell:
            await asyncio.create_subprocess_shell("python example_script.py")
        else:
            await asyncio.create_subprocess_exec("python", "example_script.py")


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [False, True])
@pytest.mark.parametrize("mode", ["shell", "exec"])
async def test_wait(fake_process, fake, mode):
    """
    Check that wait argument still works. Unfortunately asyncio doesn't have
    the timeout functionality.
    """
    shell = mode == "shell"

    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py", "wait", "stderr"],
            stdout="Stdout line 1\nStdout line 2",
            stderr="Stderr line 1",
            wait=0.5,
        )
    method = (
        asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
    )

    command = "python example_script.py wait stderr"
    if not shell:
        command = command.split()
    else:
        command = [command]

    process = await method(
        *command,
        cwd=os.path.dirname(__file__),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert process.returncode is None

    start_time = time.time()
    returncode = await process.wait()

    assert time.time() - start_time >= 0.45
    assert returncode == 0


@pytest.fixture(autouse=True)
def skip_on_pypy():
    """Async test for some reason crash on pypy 3.6 on Windows"""
    if sys.platform == "win32" and sys.version.startswith("3.6"):
        try:
            import __pypy__

            _ = __pypy__
            pytest.skip()
        except ImportError:
            pass
