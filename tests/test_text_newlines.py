import subprocess
import sys

import pytest


def _real_output(options, merge_stderr, _popen=subprocess.Popen):
    command = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.buffer.write(b'first\\r\\nsecond\\rthird\\n'); "
        "sys.stdout.buffer.flush(); "
        "sys.stderr.buffer.write(b'error\\r\\nnext\\rlast\\n')",
    ]
    with _popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
        **options,
    ) as process:
        return process.communicate()


@pytest.mark.parametrize(
    "options",
    [
        {"text": True},
        {"universal_newlines": True},
        {"encoding": "utf-8"},
        {"errors": "replace"},
        {"text": False},
        {"universal_newlines": False},
    ],
)
@pytest.mark.parametrize("registered_as_text", [False, True])
@pytest.mark.parametrize("merge_stderr", [False, True])
def test_captured_newlines_match_subprocess(
    fp, options, registered_as_text, merge_stderr
):
    expected = _real_output(options, merge_stderr)
    stdout = b"first\r\nsecond\rthird\n"
    stderr = b"error\r\nnext\rlast\n"
    if registered_as_text:
        stdout = stdout.decode("ascii")
        stderr = stderr.decode("ascii")
    fp.register(["command"], stdout=stdout, stderr=stderr)
    process = subprocess.Popen(
        ["command"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
        **options,
    )

    assert process.communicate() == expected
