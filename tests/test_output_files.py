import os
import subprocess
import sys
from tempfile import SpooledTemporaryFile

import pytest


@pytest.mark.parametrize("stream", ["stdout", "stderr", "merged"])
@pytest.mark.parametrize("spooled", [False, True], ids=["regular", "spooled"])
@pytest.mark.parametrize(
    "mode, file_options",
    [
        pytest.param("w+b", {}, id="binary"),
        pytest.param("w+", {"encoding": "utf-8"}, id="utf8"),
        pytest.param(
            "w+", {"encoding": "utf-16", "newline": "\r\n"}, id="utf16-newlines"
        ),
    ],
)
@pytest.mark.parametrize(
    "registered_output",
    [
        pytest.param(b"first\xff\r\nsecond\r", id="bytes"),
        pytest.param([b"first\xff", b"second"], id="byte-lines"),
        pytest.param("snowman \u2603\r\n", id="text"),
    ],
)
def test_redirected_output_matches_real_process(
    fp, tmp_path, stream, spooled, mode, file_options, registered_output
):
    if isinstance(registered_output, list):
        expected = b"\n".join(registered_output) + b"\n"
    elif isinstance(registered_output, str):
        expected = registered_output.encode("utf-8")
    else:
        expected = registered_output

    output_name = "stdout" if stream == "stdout" else "stderr"
    fd = 1 if stream == "stdout" else 2
    command = [sys.executable, "-c", f"import os; os.write({fd}, {expected!r})"]
    fp.pass_command(command)
    fp.register(command, **{output_name: registered_output})

    results = []
    for name in ("real", "fake"):
        if spooled:
            output = SpooledTemporaryFile(mode=mode, **file_options)
        else:
            output = (tmp_path / name).open(mode, **file_options)
        with output:
            streams = {output_name: output}
            if stream == "merged":
                streams = {"stdout": output, "stderr": subprocess.STDOUT}
            result = subprocess.run(command, check=True, **streams)
            output.flush()
            os.lseek(output.fileno(), 0, os.SEEK_SET)
            results.append(os.read(output.fileno(), len(expected) + 100))
        assert result.stdout is None
        assert result.stderr is None

    assert results[0] == expected
    assert results[1] == results[0]


def test_redirected_output_preserves_file_descriptor(fp, tmp_path):
    command = [sys.executable, "-c", "import os; os.write(1, b'child')"]
    fp.pass_command(command)
    fp.register(command, stdout=b"child")

    for name in ("real", "fake"):
        path = tmp_path / name
        with path.open("w+b") as output:
            output.write(b"before")
            output.flush()
            subprocess.run(command, stdout=output, check=True)
            assert not output.closed
            assert output.tell() == len(b"beforechild")
            output.write(b"after")
        assert path.read_bytes() == b"beforechildafter"
