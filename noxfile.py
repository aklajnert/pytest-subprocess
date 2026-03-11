import subprocess
import sys
from pathlib import Path

import nox


def _pypy311_interpreter() -> str:
    """Resolve PyPy3.11 executable explicitly on Windows.

    Work around a nox/Windows issue where unresolved interpreter aliases can
    trigger a hanging ``py -`` probe.
    """
    if sys.platform == "win32":
        try:
            result = subprocess.run(
                [
                    "py",
                    "-V:Astral/PyPy3.11.13",
                    "-c",
                    "import sys; print(sys.executable)",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass

    return "pypy3.11"


def _run_tests(session: nox.Session) -> None:
    session.install(".[test]")
    session.run(
        "pytest",
        *session.posargs,
        env={"PYTHONPATH": str(Path(__file__).resolve().parent)},
    )


@nox.session(python=["3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "3.15"])
def tests(session):
    _run_tests(session)


@nox.session(name="tests-pypy3.11", python=_pypy311_interpreter())
def tests_pypy311(session):
    _run_tests(session)


@nox.session
def flake8(session):
    session.install("flake8")
    session.run("flake8", "pytest_subprocess", "tests", *session.posargs)


@nox.session
def mypy(session):
    session.install("mypy")
    session.run("mypy", "--version")
    session.run("mypy", "pytest_subprocess", "--config-file=setup.cfg")
    session.run("mypy", "tests/test_typing.py", "--config-file=setup.cfg")


# Note sphinx-napoleon uses deprecated renames removed in 3.10
@nox.session(python="3.9")
def docs(session):
    session.install(".[docs]")
    session.run("sphinx-build", "-b", "html", "docs", "docs/_build", "-v", "-W")


@nox.session
def create_dist(session):
    session.install("twine", "build")
    session.run("python", "-m", "build")
    session.run("twine", "check", "dist/*")


@nox.session
def publish(session):
    """Publish to pypi. Run `nox publish -- prod` to publish to the official repo."""
    create_dist(session)
    twine_command = ["twine", "upload", "dist/*"]
    if "prod" not in session.posargs:
        twine_command.extend(["--repository-url", "https://test.pypi.org/legacy/"])
    session.run(*twine_command)
