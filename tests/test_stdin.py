import asyncio
import subprocess
import sys

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [False, True], ids=["real", "fake"])
@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize(
    "response",
    [{}, {"stdout": b"reply"}, {"stderr": b"reply"}, {"stdout": b"", "stderr": b""}],
    ids=["no-output", "stdout-only", "stderr-only", "empty-output"],
)
async def test_stdin_callback_preserves_output(fp, fake, asynchronous, response):
    if asynchronous and sys.platform == "win32" and hasattr(sys, "pypy_version_info"):
        pytest.skip("PyPy on Windows hangs in asyncio subprocess event loop (IOCP)")
    command = [
        sys.executable,
        "-c",
        "import sys; "
        "sys.stdout.buffer.write(b'original stdout'); "
        "sys.stderr.buffer.write(b'original stderr'); "
        "sys.stdin.buffer.read(); "
        "sys.stdout.buffer.write({!r}); sys.stderr.buffer.write({!r})".format(
            response.get("stdout", b""), response.get("stderr", b"")
        ),
    ]
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            command,
            stdout=b"original stdout",
            stderr=b"original stderr",
            stdin_callable=lambda input: response,
        )

    kwargs = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if asynchronous:
        process = await asyncio.create_subprocess_exec(*command, **kwargs)
        output = await process.communicate(input=b"input")
    else:
        with subprocess.Popen(command, **kwargs) as process:
            output = process.communicate(input=b"input")

    assert output == (
        b"original stdout" + response.get("stdout", b""),
        b"original stderr" + response.get("stderr", b""),
    )
    assert process.returncode == 0
