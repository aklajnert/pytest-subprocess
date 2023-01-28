History
=======

1.5.0 (2023-01-28)  
------------------

Features  
~~~~~~~~
* `#109 <https://github.com/aklajnert/pytest-subprocess/pull/109>`_: Match also `os.PathLike`.
* `#105 <https://github.com/aklajnert/pytest-subprocess/pull/105>`_: Add program matcher.

Other changes  
~~~~~~~~~~~~~
* `#110 <https://github.com/aklajnert/pytest-subprocess/pull/110>`_: Produce TypeError on Win Py<3.8 for Path args.

1.4.2 (2022-10-02)  
------------------

Features  
~~~~~~~~
* `#87 <https://github.com/aklajnert/pytest-subprocess/pull/87>`_: Add support for Python 3.11.
* `#80 <https://github.com/aklajnert/pytest-subprocess/pull/80>`_, `#86 <https://github.com/aklajnert/pytest-subprocess/pull/86>`_: The `register()` method returns an auxiliary object that will contain all matching `FakePopen` instances.

Bug fixes  
~~~~~~~~~
* `#93 <https://github.com/aklajnert/pytest-subprocess/pull/93>`_: Raise callback exceptions on `communicate()` calls.

Other changes  
~~~~~~~~~~~~~
* `#97 <https://github.com/aklajnert/pytest-subprocess/pull/97>`_: Fixed warnings in tests, treat warnings as errors.
* `#91 <https://github.com/aklajnert/pytest-subprocess/pull/91>`_: Use `sys.executable` instead just `"python"` in tests while invoking python subprocess.
* `#90 <https://github.com/aklajnert/pytest-subprocess/pull/90>`_: Fix documentation build, add CI check for it.

1.4.1 (2022-02-09)  
------------------

Other changes  
~~~~~~~~~~~~~
* `#74 <https://github.com/aklajnert/pytest-subprocess/pull/74>`_: Add ``fp`` alias for the fixture, and ``register`` for the ``regisiter_subprocess``.

1.4.0 (2022-01-23)  
------------------

Features  
~~~~~~~~
* `#71 <https://github.com/aklajnert/pytest-subprocess/pull/71>`_: Add support for stdin with asyncio.

Bug fixes  
~~~~~~~~~
* `#68 <https://github.com/aklajnert/pytest-subprocess/pull/68>`_: Make `stdout` and `stderr` an `asyncio.StreamReader` instance when using asyncio functions.
* `#63 <https://github.com/aklajnert/pytest-subprocess/pull/63>`_, `#67 <https://github.com/aklajnert/pytest-subprocess/pull/67>`_: Add missing items to `asyncio.subprocess`.

Other changes  
~~~~~~~~~~~~~
* `#69 <https://github.com/aklajnert/pytest-subprocess/pull/69>`_: Extracted code into separate files to improve navigation.

1.3.2 (2021-11-07)  
------------------

Bug fixes  
~~~~~~~~~
* `#61 <https://github.com/aklajnert/pytest-subprocess/pull/61>`_: Fixed behavior of ``asyncio.create_subproess_exec()``.

1.3.1 (2021-11-01)  
------------------

Bug fixes  
~~~~~~~~~
* `#58 <https://github.com/aklajnert/pytest-subprocess/pull/58>`_: Correctly handle file stream output.

1.3.0 (2021-10-24)  
------------------

Features  
~~~~~~~~
* `#55 <https://github.com/aklajnert/pytest-subprocess/pull/55>`_: Add support for ``terminate()``, ``kill()``, ``send_signal()``.

1.2.0 (2021-10-09)  
------------------

Features  
~~~~~~~~
* `#49 <https://github.com/aklajnert/pytest-subprocess/pull/49>`_, `#52 <https://github.com/aklajnert/pytest-subprocess/pull/52>`_: Add support for ``asyncio``.

Other changes  
~~~~~~~~~~~~~
* `#50 <https://github.com/aklajnert/pytest-subprocess/pull/50>`_: Change docs theme.

1.1.2 (2021-07-17)  
------------------

Bug fixes  
~~~~~~~~~
* `#47 <https://github.com/aklajnert/pytest-subprocess/pull/47>`_: Prevent `allow_unregistered()` and `keep_last_process()` from affecting other tests.

1.1.1 (2021-06-18)  
------------------

Bug fixes  
~~~~~~~~~
* `#43 <https://github.com/aklajnert/pytest-subprocess/pull/43>`_: Wait for callback thread to finish when calling ``communicate()``.

Other changes  
~~~~~~~~~~~~~
* `#42 <https://github.com/aklajnert/pytest-subprocess/pull/42>`_: Fix type annotations for `register_subprocess()`.

1.1.0 (2021-04-18)  
------------------

Bug fixes  
~~~~~~~~~
* `#37 <https://github.com/aklajnert/pytest-subprocess/pull/37>`_: Preserve original command in `proc.args` to prevent leaking the internal `Command` type.

Other changes  
~~~~~~~~~~~~~
* `#38 <https://github.com/aklajnert/pytest-subprocess/pull/38>`_: Switched CI from Azure Pipelines to GitHub Actions.
* `#35 <https://github.com/aklajnert/pytest-subprocess/pull/35>`_: Drop support for python 3.4 and 3.5. Move type annotations from `.pyi` files into sources.

1.0.1 (2021-03-20)  
------------------

Bug fixes  
~~~~~~~~~
* `#34 <https://github.com/aklajnert/pytest-subprocess/pull/34>`_: Prevent appending newlines to outputs unless defined as list/tuple.

Other changes  
~~~~~~~~~~~~~
* `#32 <https://github.com/aklajnert/pytest-subprocess/pull/32>`_: Make the ``Command`` class iterable.

1.0.0 (2020-08-22)  
------------------

Features  
~~~~~~~~
* `#29 <https://github.com/aklajnert/pytest-subprocess/pull/29>`_: Remember subprocess calls to check if expected commands were executed.
* `#28 <https://github.com/aklajnert/pytest-subprocess/pull/28>`_: Allow to match a command with variable arguments (non-exact matching).

0.1.5 (2020-06-19)  
------------------

Bug fixes  
~~~~~~~~~
* `#26 <https://github.com/aklajnert/pytest-subprocess/pull/26>`_: `encoding` and `errors` arguments will properly trigger `text` mode.

0.1.4 (2020-04-28)  
------------------

Bug fixes  
~~~~~~~~~
* `#22 <https://github.com/aklajnert/pytest-subprocess/pull/22>`_: The `returncode` will not be ignored when `callback` is used.
* `#21 <https://github.com/aklajnert/pytest-subprocess/pull/21>`_: The exception raised from callback will take precedence over those from subprocess.
* `#20 <https://github.com/aklajnert/pytest-subprocess/pull/20>`_: Registering process will be now consistent regardless of the command type.
* `#19 <https://github.com/aklajnert/pytest-subprocess/pull/19>`_: Fixed crash for stderr redirect with an empty stream definition.

0.1.3 (2020-03-04)  
------------------

Features  
~~~~~~~~
* `#13 <https://github.com/aklajnert/pytest-subprocess/pull/13>`_: Allow passing keyword arguments into callbacks.

Bug fixes  
~~~~~~~~~
* `#12 <https://github.com/aklajnert/pytest-subprocess/pull/12>`_: Properly raise exceptions from callback functions.

Documentation changes  
~~~~~~~~~~~~~~~~~~~~~
* `#15 <https://github.com/aklajnert/pytest-subprocess/pull/15>`_: Add documentation chapter about the callback functions.

0.1.2 (2020-01-17)  
------------------

Features  
~~~~~~~~
* `#3 <https://github.com/aklajnert/pytest-subprocess/pull/3>`_: Add basic support for process input.

Bug fixes  
~~~~~~~~~
* `#5 <https://github.com/aklajnert/pytest-subprocess/pull/5>`_: Make ``wait()`` method to raise ``TimeoutError`` after the desired time will elapse.

Documentation changes  
~~~~~~~~~~~~~~~~~~~~~
* `#7 <https://github.com/aklajnert/pytest-subprocess/pull/7>`_, `#8 <https://github.com/aklajnert/pytest-subprocess/pull/8>`_, `#9 <https://github.com/aklajnert/pytest-subprocess/pull/9>`_: Create Sphinx documentation.

Other changes  
~~~~~~~~~~~~~
* `#10 <https://github.com/aklajnert/pytest-subprocess/pull/10>`_:  Switch from ``tox`` to ``nox`` for running tests and tasks.
* `#4 <https://github.com/aklajnert/pytest-subprocess/pull/4>`_: Add classifier for Python 3.9. Update CI config to test also on that interpreter version.

0.1.1 (2019-11-24)  
------------------

Other changes  
~~~~~~~~~~~~~
* `#1 <https://github.com/aklajnert/pytest-subprocess/pull/1>`_, `#2 <https://github.com/aklajnert/pytest-subprocess/pull/2>`_: Enable support for Python 3.4, add CI tests for that version.

0.1.0 (2019-11-23)  
------------------

Initial release  
