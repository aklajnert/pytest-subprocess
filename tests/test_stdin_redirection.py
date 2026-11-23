import asyncio
import subprocess
import sys
import tempfile

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [False, True], ids=["real", "fake"])
@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize(
    "destination", ["file", "pipe", "devnull", "merged-file", "merged-pipe"]
)
@pytest.mark.parametrize("stream", ["stdout", "stderr"])
async def test_stdin_callback_respects_output_destination(
    fp, fake, asynchronous, destination, stream
):
    if asynchronous and sys.platform == "win32" and hasattr(sys, "pypy_version_info"):
        pytest.skip("PyPy on Windows hangs in asyncio subprocess event loop (IOCP)")
    initial = b"before\r\n"
    response = b"after\xff\r\n"
    command = [
        sys.executable,
        "-c",
        "import sys; output = sys.{}.buffer; "
        "output.write({!r}); output.flush(); "
        "sys.stdin.buffer.read(); output.write({!r}); output.flush()".format(
            stream, initial, response
        ),
    ]
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            command,
            **{stream: initial},
            stdin_callable=lambda _: {stream: response},
        )

    with tempfile.TemporaryFile("w+b") as output_file:
        target = {
            "file": output_file,
            "pipe": subprocess.PIPE,
            "devnull": subprocess.DEVNULL,
            "merged-file": output_file,
            "merged-pipe": subprocess.PIPE,
        }[destination]
        kwargs = dict(
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        captured_stream = stream
        if destination.startswith("merged"):
            kwargs.update(stdout=target, stderr=subprocess.STDOUT)
            captured_stream = "stdout"
        else:
            kwargs[stream] = target

        if asynchronous:
            process = await asyncio.create_subprocess_exec(*command, **kwargs)
            actual = await process.communicate(input=b"input")
        else:
            with subprocess.Popen(command, **kwargs) as process:
                actual = process.communicate(input=b"input")

        expected = initial + response
        if destination.endswith("pipe"):
            assert actual == (
                expected if captured_stream == "stdout" else None,
                expected if captured_stream == "stderr" else None,
            )
        else:
            assert actual == (None, None)
        output_file.seek(0)
        assert output_file.read() == (expected if destination.endswith("file") else b"")
        assert process.returncode == 0
