from pathlib import Path

import nox


@nox.session(python=["3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "pypy3.8"])
def tests(session):
    session.install(".[test]")
    session.run(
        "pytest",
        *session.posargs,
        env={"PYTHONPATH": str(Path(__file__).resolve().parent)}
    )


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
