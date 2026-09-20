import subprocess
import sys
import threading

import pytest


@pytest.mark.parametrize("fake", [False, True], ids=["real", "fake"])
@pytest.mark.parametrize("method", ["wait", "communicate"])
@pytest.mark.parametrize("timeout", [0, 0.01])
def test_timeout_does_not_finish_running_callback(fp, tmp_path, fake, method, timeout):
    release = threading.Event()
    release_path = tmp_path / "release"
    command = [
        sys.executable,
        "-c",
        "import pathlib, sys, time\n"
        "while not pathlib.Path(sys.argv[1]).exists():\n"
        "    time.sleep(0.01)\n"
        "sys.exit(7)\n",
        str(release_path),
    ]

    def callback(process):
        release.wait()

    fp.allow_unregistered(not fake)
    if fake:
        fp.register(command, callback=callback, returncode=7)

    process = subprocess.Popen(command)
    try:
        for _ in range(2):
            with pytest.raises(subprocess.TimeoutExpired) as exc:
                getattr(process, method)(timeout=timeout)
            assert exc.value.cmd == command
            if fake:
                assert exc.value.timeout == timeout
            assert process.returncode is None
            assert process.poll() is None
    finally:
        release.set()
        release_path.touch()
        process.wait(timeout=5)

    assert process.returncode == 7
    assert process.poll() == 7
    assert process.wait(timeout=0) == 7
    assert process.communicate(timeout=0) == (None, None)
