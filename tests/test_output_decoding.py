import io
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("fake", [False, True], ids=["real", "fake"])
@pytest.mark.parametrize(
    "data,options,expected",
    [
        (b"caf\xe9", {"encoding": "latin-1"}, "caf\u00e9"),
        ("snowman \u2603".encode("utf-16"), {"encoding": "utf-16"}, "snowman \u2603"),
        (b"a\xffb", {"encoding": "utf-8", "errors": "replace"}, "a\ufffdb"),
        (b"a\xffb", {"encoding": "utf-8", "errors": "ignore"}, "ab"),
        (b"plain", {"errors": "replace"}, "plain"),
    ],
)
def test_output_decoding(fp, fake, data, options, expected):
    command = [
        sys.executable,
        "-c",
        f"import os; os.write(1, {data!r}); os.write(2, {data!r})",
    ]
    if fake:
        fp.register(command, stdout=data, stderr=data)
    else:
        fp.pass_command(command)

    result = subprocess.run(command, capture_output=True, check=True, **options)

    assert result.stdout == expected
    assert result.stderr == expected


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_output_lines_decoding(fp, stream):
    fp.register(["command"], **{stream: [b"caf\xe9", b"a\xffb"]})

    result = subprocess.run(
        ["command"], capture_output=True, encoding="ascii", errors="replace"
    )

    assert getattr(result, stream) == f"caf\ufffd{os.linesep}a\ufffdb{os.linesep}"


def test_stdin_callback_output_decoding(fp):
    fp.register(
        ["command"],
        stdout=b"caf\xe9",
        stdin_callable=lambda _: {"stdout": b"\xe9", "stderr": b"\xff"},
    )

    result = subprocess.run(
        ["command"], input="input", capture_output=True, encoding="latin-1"
    )

    assert result.stdout == "caf\u00e9\u00e9"
    assert result.stderr == "\u00ff"


@pytest.mark.parametrize("fake", [False, True], ids=["real", "fake"])
def test_strict_decoding_errors(fp, fake):
    command = [sys.executable, "-c", "import os; os.write(1, b'\\xff')"]
    if fake:
        fp.register(command, stdout=b"\xff")
    else:
        fp.pass_command(command)

    with pytest.raises(UnicodeDecodeError):
        subprocess.check_output(command, encoding="ascii")


@pytest.mark.skipif(sys.version_info < (3, 10), reason="locale encoding needs 3.10")
def test_locale_encoding(fp):
    with io.TextIOWrapper(io.BytesIO(), encoding="locale") as buffer:
        data = "caf\u00e9".encode(buffer.encoding)
    fp.register(["command"], stdout=data, stderr=data)

    result = subprocess.check_output(
        ["command"], stderr=subprocess.STDOUT, encoding="locale"
    )

    assert result == "caf\u00e9caf\u00e9"


@pytest.mark.parametrize("fake", [False, True], ids=["real", "fake"])
def test_empty_encoding_is_invalid(fp, fake):
    command = [sys.executable, "-c", "pass"]
    if fake:
        fp.register(command)
    else:
        fp.pass_command(command)

    with pytest.raises(LookupError):
        subprocess.check_output(command, text=True, encoding="")


@pytest.mark.parametrize(
    "output,options,expected",
    [(b"\xff", {}, b"\xff"), ("caf\u00e9", {"encoding": "ascii"}, "caf\u00e9")],
)
def test_output_without_decoding(fp, output, options, expected):
    fp.register(["command"], stdout=output)

    assert subprocess.check_output(["command"], **options) == expected
