import asyncio
import gc
import subprocess
import threading
import weakref
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pytest_subprocess import fake_popen


class Callback:
    def __init__(self, error=None):
        self.loop = asyncio.get_running_loop()
        self.started = asyncio.Event()
        self.finished = asyncio.Event()
        self.release = threading.Event()
        self.calls = 0
        self.error = error

    def __call__(self, process):
        self.calls += 1
        self.loop.call_soon_threadsafe(self.started.set)
        try:
            if not self.release.wait(5):
                raise RuntimeError("Test did not release callback")
            if self.error:
                process.returncode = 1
                raise self.error
        finally:
            self.loop.call_soon_threadsafe(self.finished.set)


@pytest.mark.asyncio
async def test_concurrent_wait_and_communicate_execute_callback_once(fp, monkeypatch):
    callback = Callback()
    fp.register(["worker"], callback=callback, stdout=b"output", returncode=7)
    process = await asyncio.create_subprocess_exec(
        "worker", stdout=asyncio.subprocess.PIPE
    )
    assert callback.calls == 0
    eof = Mock(wraps=process.stdout.feed_eof)
    monkeypatch.setattr(process.stdout, "feed_eof", eof)
    waiters = [
        asyncio.create_task(process.wait()),
        asyncio.create_task(process.wait()),
        asyncio.create_task(process.communicate()),
    ]
    try:
        await callback.started.wait()
    finally:
        callback.release.set()
        results = await asyncio.gather(*waiters)
    assert results == [7, 7, (b"output", None)]
    assert callback.calls == 1
    eof.assert_called_once_with()
    assert await process.wait() == 7


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["wait", "communicate"])
@pytest.mark.parametrize("cancel_all", [False, True])
async def test_cancel_waiter_does_not_block_or_restart_callback(fp, method, cancel_all):
    callback = Callback()
    fp.register(["worker"], callback=callback, stdout=b"output", returncode=7)
    process = await asyncio.create_subprocess_exec(
        "worker", stdout=asyncio.subprocess.PIPE
    )
    first = asyncio.create_task(getattr(process, method)())
    await callback.started.wait()
    second = asyncio.create_task(process.wait())
    await asyncio.sleep(0)
    rescued = threading.Event()

    def rescue():
        rescued.set()
        callback.release.set()

    # A separate thread prevents a broken implementation from deadlocking the test.
    watchdog = threading.Timer(1, rescue)
    watchdog.start()
    try:
        first.cancel()
        cancelled = [first]
        if cancel_all:
            second.cancel()
            cancelled.append(second)
        results = await asyncio.gather(*cancelled, return_exceptions=True)
        assert all(isinstance(result, asyncio.CancelledError) for result in results)
        assert not rescued.is_set()
        assert process.returncode is None
        if not cancel_all:
            assert not second.done()
    finally:
        callback.release.set()
        await asyncio.gather(first, second, return_exceptions=True)
        watchdog.cancel()
        watchdog.join()

    # Completion and EOF must not require a surviving wait() caller.
    assert await asyncio.wait_for(process.stdout.read(), 2) == b"output"
    assert process.returncode == 7
    assert await process.wait() == 7
    assert callback.calls == 1


@pytest.mark.asyncio
async def test_callback_exception_is_shared_by_waiters_and_retries(fp):
    error = ValueError("callback failed")
    callback = Callback(error)
    fp.register(["worker"], callback=callback)
    process = await asyncio.create_subprocess_exec("worker")
    first = asyncio.create_task(process.wait())
    second = asyncio.create_task(process.wait())
    try:
        await callback.started.wait()
    finally:
        callback.release.set()
        results = await asyncio.gather(first, second, return_exceptions=True)
    assert results == [error, error]
    with pytest.raises(ValueError) as exc:
        await process.communicate()
    assert exc.value is error
    assert process.returncode == 1
    assert callback.calls == 1


@pytest.mark.asyncio
async def test_abandoned_callback_exception_is_retrieved(fp):
    callback = Callback(ValueError("unobserved callback"))
    recorder = fp.register(["worker"], callback=callback)
    process = await asyncio.create_subprocess_exec("worker")
    waiter = asyncio.create_task(process.wait())
    await callback.started.wait()
    loop = asyncio.get_running_loop()
    errors = []
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda loop, context: errors.append(context))
    watchdog = threading.Timer(1, callback.release.set)
    watchdog.start()
    try:
        waiter.cancel()
        await asyncio.gather(waiter, return_exceptions=True)
        callback.release.set()
        await callback.finished.wait()
        reference = weakref.ref(process)
        # The fixture's process recorder also retains this instance.
        recorder.calls.clear()
        callback.error = None
        del process, waiter
        for _ in range(10):
            await asyncio.sleep(0.01)
            gc.collect()
            if reference() is None:
                break
        assert reference() is None
        assert errors == []
    finally:
        callback.release.set()
        watchdog.cancel()
        watchdog.join()
        loop.set_exception_handler(previous_handler)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["callback", "delay"])
@pytest.mark.parametrize("method", ["wait", "communicate", "wait_for"])
async def test_timeout_only_stops_its_waiter(fp, monkeypatch, kind, method):
    callback = Callback()
    if kind == "delay":
        # Control the registered delay without depending on elapsed wall time.
        monkeypatch.setattr(fake_popen, "time", SimpleNamespace(sleep=callback))
        fp.register(["worker"], wait=10, returncode=7, stdout=b"output")
    else:
        fp.register(["worker"], callback=callback, returncode=7, stdout=b"output")
    process = await asyncio.create_subprocess_exec(
        "worker", stdout=asyncio.subprocess.PIPE
    )
    eof = Mock(wraps=process.stdout.feed_eof)
    monkeypatch.setattr(process.stdout, "feed_eof", eof)
    waiter = asyncio.create_task(process.wait())
    await callback.started.wait()
    rescued = threading.Event()

    def rescue():
        rescued.set()
        callback.release.set()

    watchdog = threading.Timer(1, rescue)
    watchdog.start()
    expected = (
        subprocess.TimeoutExpired
        if kind == "delay" and method == "wait"
        else asyncio.TimeoutError
    )
    try:
        with pytest.raises(expected):
            if method == "wait_for":
                await asyncio.wait_for(process.wait(), timeout=0.01)
            else:
                await getattr(process, method)(timeout=0.01)
        assert not rescued.is_set()
        assert process.returncode is None
        assert not waiter.done()
    finally:
        callback.release.set()
        result = await waiter
        watchdog.cancel()
        watchdog.join()
    assert result == 7
    assert callback.calls == 1
    assert await process.communicate(timeout=0) == (b"output", None)
    assert await process.wait(timeout=0) == 7
    eof.assert_called_once_with()
