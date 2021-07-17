from pathlib import Path

import pytest
from docutils.core import publish_doctree

ROOT_DIR = Path(__file__).parents[1]


def is_code_block(node):
    return node.tagname == "literal_block" and "code" in node.attributes["classes"]


def get_code_blocks(file_path):
    with file_path.open() as file_handle:
        content = file_handle.read()

    code_blocks = publish_doctree(content).traverse(condition=is_code_block)
    return [block.astext() for block in code_blocks]


@pytest.mark.parametrize("rst_file", ("docs/index.rst", "README.rst"))
def test_documentation(testdir, rst_file):
    imports = "\n".join(
        [
            "import os",
            "",
            "import pytest",
            "import pytest_subprocess",
            "import subprocess",
        ]
    )

    setup_fixture = (
        "\n\n"
        "@pytest.fixture(autouse=True)\n"
        "def setup():\n"
        "    os.chdir(os.path.dirname(__file__))\n\n"
    )

    code_blocks = "\n".join(get_code_blocks(ROOT_DIR / rst_file))
    testdir.makepyfile(imports + setup_fixture + "\n" + code_blocks)

    result = testdir.inline_run()
    assert result.ret == 0
