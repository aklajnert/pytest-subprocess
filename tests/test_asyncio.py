import asyncio
import os
import sys
import time

import anyio
import pytest

from pytest_subprocess.fake_popen import AsyncFakePopen

PYTHON = sys.executable


@pytest.fixture()
def event_loop_policy(request):
    if sys.platform.startswith("win"):
        if request.node.name.startswith("test_invalid_event_loop"):
            return asyncio.WindowsSelectorEventLoopPolicy()
        else:
            return asyncio.WindowsProactorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


if sys.platform.startswith("win") and sys.version_info < (3, 8):

    @pytest.fixture(autouse=True)
    def event_loop(request, event_loop_policy):
        loop = event_loop_policy.new_event_loop()
        yield loop
        loop.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["shell", "exec"])
async def test_basic_usage(fp, mode):
    shell = mode == "shell"
    fp.register(["some-command-that-is-definitely-unavailable"], returncode=500)
    method = (
        asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
    )
    process = await method("some-command-that-is-definitely-unavailable")
    returncode = await process.wait()

    assert process.returncode == returncode
    assert process.returncode == 500


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [True, False])
async def test_with_arguments_shell(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=["Stderr line 1"],
        )

    process = await asyncio.create_subprocess_shell(
        f"{PYTHON} example_script.py stderr",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate()

    assert err == os.linesep.encode().join([b"Stderr line 1", b""])
    assert out == os.linesep.encode().join([b"Stdout line 1", b"Stdout line 2", b""])
    assert process.returncode == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [True, False])
async def test_with_arguments_exec(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=["Stderr line 1"],
        )

    process = await asyncio.create_subprocess_exec(
        PYTHON,
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
async def test_incorrect_call(fp, fake, mode):
    """Asyncio doesn't support command as a list"""
    shell = mode == "shell"
    fp.allow_unregistered(not fake)
    if fake:
        fp.register(["test"])

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
async def test_invalid_event_loop(fp, fake, mode):
    """
    The event_loop is changed by the `event_loop` fixture based on
    the test name (hack).
    """
    shell = mode == "shell"
    fp.allow_unregistered(not fake)
    if fake:
        fp.register([PYTHON, "example_script.py"])

    with pytest.raises(NotImplementedError):
        if shell:
            await asyncio.create_subprocess_shell(f"{PYTHON} example_script.py")
        else:
            await asyncio.create_subprocess_exec(PYTHON, "example_script.py")


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [False, True])
@pytest.mark.parametrize("mode", ["shell", "exec"])
async def test_wait(fp, fake, mode):
    """
    Check that wait argument still works. Unfortunately asyncio doesn't have
    the timeout functionality.
    """
    shell = mode == "shell"

    fp.allow_unregistered(not fake)
    if fake:
        fp.register(
            [PYTHON, "example_script.py", "wait", "stderr"],
            stdout="Stdout line 1\nStdout line 2",
            stderr="Stderr line 1",
            wait=0.5,
        )
    method = (
        asyncio.create_subprocess_shell if shell else asyncio.create_subprocess_exec
    )

    command = f"{PYTHON} example_script.py wait stderr"
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


@pytest.mark.asyncio
async def test_devnull_stdout(fp):
    """From GitHub #63 - make sure all the `asyncio.subprocess` consts are available."""
    fp.register("cat")

    await asyncio.create_subprocess_exec(
        "cat",
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.STDOUT,
        stderr=asyncio.subprocess.PIPE,
    )


@pytest.mark.asyncio
async def test_anyio(fp):
    await anyio.sleep(0.01)


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [False, True])
async def test_stdout_and_stderr(fp, fake):
    if fake:
        fp.register(
            [PYTHON, "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=["Stderr line 1"],
        )
    else:
        fp.allow_unregistered(True)

    process = await asyncio.create_subprocess_exec(
        PYTHON,
        "example_script.py",
        "stderr",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_list = []
    stderr_list = []

    loop = asyncio.get_event_loop()
    await asyncio.gather(
        loop.create_task(_read_stream(process.stdout, stdout_list)),
        loop.create_task(_read_stream(process.stderr, stderr_list)),
        loop.create_task(process.wait()),
    )

    assert stdout_list == [f"Stdout line 1{os.linesep}", f"Stdout line 2{os.linesep}"]
    assert stderr_list == [f"Stderr line 1{os.linesep}"]


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [False, True])
async def test_combined_stdout_and_stderr(fp, fake):
    if fake:
        fp.register(
            [PYTHON, "example_script.py", "stderr"],
            stdout=["Stdout line 1", "Stdout line 2"],
            stderr=["Stderr line 1"],
        )
    else:
        fp.allow_unregistered(True)

    process = await asyncio.create_subprocess_exec(
        PYTHON,
        "example_script.py",
        "stderr",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    stdout_list = []
    stderr_list = []

    loop = asyncio.get_event_loop()
    await asyncio.gather(
        loop.create_task(_read_stream(process.stdout, stdout_list)),
        loop.create_task(_read_stream(process.stderr, stderr_list)),
        loop.create_task(process.wait()),
    )

    # sorted() is necessary here, as the order here may be not deterministic,
    # and sometimes stderr comes before stdout or the opposite
    assert sorted(stdout_list) == [
        f"Stderr line 1{os.linesep}",
        f"Stdout line 1{os.linesep}",
        f"Stdout line 2{os.linesep}",
    ]
    assert stderr_list == ["empty"]


async def _read_stream(stream: asyncio.StreamReader, output_list):
    if stream is None:
        output_list.append("empty")
        return None

    while True:
        line = await stream.readline()
        if not line:
            break
        else:
            output_list.append(line.decode())


@pytest.mark.asyncio
@pytest.mark.parametrize("fake", [False, True])
async def test_input(fp, fake):
    fp.allow_unregistered(not fake)
    if fake:

        def stdin_callable(input):
            return {
                "stdout": "Provide an input: Provided: {data}".format(
                    data=input.decode()
                )
            }

        fp.register(
            [PYTHON, "example_script.py", "input"],
            stdout=[b"Stdout line 1", b"Stdout line 2"],
            stdin_callable=stdin_callable,
        )

    process = await asyncio.create_subprocess_exec(
        PYTHON,
        "example_script.py",
        "input",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate(input=b"test")

    assert out.splitlines() == [
        b"Stdout line 1",
        b"Stdout line 2",
        b"Provide an input: Provided: test",
    ]
    assert err is None


@pytest.mark.asyncio
async def test_popen_recorder(fp):
    recorder = fp.register(["test_script"], occurrences=2)
    assert recorder.call_count() == 0

    await asyncio.create_subprocess_exec("test_script")
    assert recorder.call_count() == 1
    await asyncio.create_subprocess_shell("test_script")
    assert recorder.call_count() == 2

    assert all(isinstance(instance, AsyncFakePopen) for instance in recorder.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "callback",
    [
        pytest.param(None, id="no-callback"),
        pytest.param(
            lambda process: process,
            id="with-callback",
        ),
    ],
)
async def test_asyncio_subprocess_using_callback(callback, fp):
    async def my_async_func():
        process = await asyncio.create_subprocess_exec(
            "test",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.wait()
        return await process.stdout.read()

    fp.register(["test"], stdout=b"fizz", callback=callback)
    assert await my_async_func() == b"fizz"


@pytest.mark.asyncio
async def test_asyncio_subprocess_using_communicate_with_callback_kwargs(fp):
    expected_some_value = 2

    def cbk(fake_obj, some_value=None):
        assert expected_some_value == some_value
        return fake_obj

    async def my_async_func():
        process = await asyncio.create_subprocess_exec(
            "test",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await process.communicate()
        return out

    fp.register(
        ["test"],
        stdout=b"fizz",
        callback=cbk,
        callback_kwargs={"some_value": expected_some_value},
    )
    assert await my_async_func() == b"fizz"


@pytest.mark.asyncio
async def test_process_recorder_args(fp):
    fp.keep_last_process(True)
    recorder = fp.register(["test_script", fp.any()])
    await asyncio.create_subprocess_exec(
        "test_script",
        "arg1",
        env={"foo": "bar"},
    )

    assert recorder.call_count() == 1
    assert recorder.calls[0].args == ["test_script", "arg1"]
    assert recorder.calls[0].kwargs == {"env": {"foo": "bar"}}


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
