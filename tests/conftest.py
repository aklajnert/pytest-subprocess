import asyncio
import faulthandler
import os
import sys

import pytest

pytest_plugins = "pytester"
faulthandler.enable(file=sys.stderr, all_threads=True)


@pytest.fixture(autouse=True)
def event_loop(request):
    policy = asyncio.get_event_loop_policy()
    if sys.platform == "win32":
        if request.node.name.startswith("test_invalid_event_loop"):
            loop = asyncio.SelectorEventLoop()
        else:
            loop = asyncio.ProactorEventLoop()
    else:
        loop = policy.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup():
    os.chdir(os.path.dirname(__file__))
