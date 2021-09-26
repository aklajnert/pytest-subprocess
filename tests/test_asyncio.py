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
@pytest.mark.parametrize("shell", [True, False])
async def test_basic_usage(fake_process, shell):
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
@pytest.mark.parametrize("shell", [True, False])
async def test_basic_usage_with_real(fake_process, fake, shell):
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(
            ["python", "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=["Stderr line 1"],
        )

    method = (
        asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
    )

    process = await method(
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
@pytest.mark.parametrize("shell", [True, False])
async def test_incorrect_call(fake_process, fake, shell):
    """Asyncio doesn't support command as a list"""
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(["test"])

    method = (
        asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
    )

    with pytest.raises(ValueError, match="cmd must be a string"):
        await method(["test"])


@pytest.mark.asyncio
@pytest.mark.skipif('sys.platform!="win32"')
@pytest.mark.parametrize("fake", [True, False])
@pytest.mark.parametrize("shell", [True, False])
async def test_invalid_event_loop(fake_process, fake, shell):
    """
    The event_loop is changed by the `event_loop` fixture based on
    the test name (hack).
    """
    fake_process.allow_unregistered(not fake)
    if fake:
        fake_process.register_subprocess(["python", "example_script.py"])

    method = (
        asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
    )

    with pytest.raises(NotImplementedError):
        await method("python example_script.py")


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [False, True])
@pytest.mark.parametrize("shell", [True, False])
async def test_wait(fake_process, fake, shell):
    """
    Check that wait argument still works. Unfortunately asyncio doesn't have
    the timeout functionality.
    """
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

    process = await method(
        ("python example_script.py wait stderr"),
        cwd=os.path.dirname(__file__),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert process.returncode is None

    start_time = time.time()
    returncode = await process.wait()

    assert time.time() - start_time >= 0.5
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
