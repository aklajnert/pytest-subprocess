import faulthandler
import os
import sys

import pytest

pytest_plugins = "pytester"
faulthandler.enable(file=sys.stderr, all_threads=True)


@pytest.fixture(autouse=True)
def setup():
    os.chdir(os.path.dirname(__file__))
