# AGENTS.md

Guidance for AI coding agents working on `pytest-subprocess`.

## Project overview

- `pytest-subprocess` is a pytest plugin that fakes `subprocess` (hooks `subprocess.Popen`,
  so `run()`, `call()`, `check_call()`, `check_output()` and `asyncio` subprocess creation work too).
- Main code: `pytest_subprocess/` (`fake_process.py`, `fixtures.py`, `utils.py`, `exceptions.py`).
- Tests: `tests/`. Docs: `docs/` (Sphinx). Full usage docs are in `README.rst` and `docs/usage.rst`.

## How to run tests

- Fastest: `python -m pytest` (or `uv run pytest` inside a `uv venv`).
- Full matrix: `nox -s tests-<python-version>` (e.g. `nox -s tests-3.12`).
- Type check: `nox -s mypy` (config in `setup.cfg`).
- Lint: `nox -s flake8` (max line length 89, see `setup.cfg`).
- Docs build: `nox -s docs`.
- Keep test coverage at least at the same level; CI runs tests on Linux/macOS/Windows
  plus mypy, flake8, and docs.

## Code style

- Follow existing style in `pytest_subprocess/` (typed code, `setup.cfg` mypy settings apply).
- Line length: 89 (flake8 config).
- New features should come with tests in `tests/` mirroring existing patterns
  (use the `fp` / `fake_process` fixture).

## Changelog (required for every PR)

Every pull request MUST include a changelog entry managed with
[changelogd](https://changelogd.readthedocs.io/en/latest/).

- Do NOT edit `HISTORY.rst` by hand — it is generated from `changelog.d/` at release time.
- Prefer running changelogd via [`uvx`](https://docs.astral.sh/uv/guides/tools/)
  so no local install is needed: `uvx changelogd ...`
- Create one entry per PR with:

  ```sh
  uvx changelogd entry --type <type> --message "<message>" --pr-ids <PR-number>
  ```

- Valid `--type` values (see `changelog.d/config.yaml`):
  `feature`, `bug`, `doc`, `deprecation`, `other`.
- If the PR number is not known yet, omit `--pr-ids` (it can be added later);
  `--message` is always required.
- Keep the entry consistent in style and scope with previous entries
  (see `changelog.d/releases/` and `HISTORY.rst`): one short, single-sentence,
  user-facing message per PR, imperative mood, ending with a period —
  e.g. `Add ...`, `Fix ...`, `Support ...` — describing the behavior change,
  not implementation details.
- Examples:

  ```sh
  uvx changelogd entry --type feature --message "Add fp.regex() for regex-based argument matching." --pr-ids 206
  uvx changelogd entry --type bug --message "Fix poll() not reflecting returncode with a registered callback." --pr-ids 207
  ```

- Verify with `uvx changelogd draft` (prints the unreleased changelog to stdout).
- Never run `uvx changelogd release` or `uvx changelogd partial` in a PR —
  releases are done by maintainers.
