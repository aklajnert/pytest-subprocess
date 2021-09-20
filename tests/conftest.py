import os

import pytest

pytest_plugins = "pytester"


@pytest.fixture(autouse=True)
def setup():
    os.chdir(os.path.dirname(__file__))
