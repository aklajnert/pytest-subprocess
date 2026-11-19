import subprocess
import sys

import pytest

_CHILD = (
    "import sys; data = sys.stdin.buffer.read(); "
    "sys.stdout.buffer.write(b'reply' if data else b'')"
)


def _real_communicate_twice(first_input, second_input, _popen=subprocess.Popen):
    process = _popen(
        [sys.executable, "-c", _CHILD],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    first_result = process.communicate(input=first_input)
    try:
        second_result = ("result", process.communicate(input=second_input))
    except ValueError as error:
        second_result = ("error", str(error))
    return first_result, second_result


@pytest.mark.parametrize(
    "first_input, first_output",
    [(None, b""), (b"", b""), (b"first", b"reply")],
)
def test_communicate_rejects_input_after_communication_started(
    fp, first_input, first_output
):
    received = []
    fp.register(
        ["command"],
        stdin_callable=lambda data: (received.append(data) or {"stdout": b"reply"}),
    )

    process = subprocess.Popen(
        ["command"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    assert process.communicate(input=first_input) == (first_output, None)

    with pytest.raises(
        ValueError, match="Cannot send input after starting communication"
    ):
        process.communicate(input=b"second")

    assert received == ([first_input] if first_input else [])


@pytest.mark.parametrize("first_input", [None, b"", b"data"])
@pytest.mark.parametrize("second_input", [None, b"", b"data"])
def test_communicate_input_truthiness_matches_subprocess(fp, first_input, second_input):
    real_result = _real_communicate_twice(first_input, second_input)

    fp.register(
        ["command"],
        stdin_callable=lambda data: {"stdout": b"reply"},
    )
    process = subprocess.Popen(
        ["command"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    first_result = process.communicate(input=first_input)
    try:
        second_result = ("result", process.communicate(input=second_input))
    except ValueError as error:
        second_result = ("error", str(error))

    assert (first_result, second_result) == real_result
