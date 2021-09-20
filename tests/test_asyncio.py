import asyncio
import os
import sys

import pytest


@pytest.fixture(autouse=True)
def event_loop(request):
    policy = asyncio.get_event_loop_policy()
    if sys.platform == "win32":
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
        f"python example_script.py stderr",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate()

    assert err == os.linesep.encode().join([b"Stderr line 1", b""])
    assert out == os.linesep.encode().join([b"Stdout line 1", b"Stdout line 2", b""])
    assert process.returncode == 0
