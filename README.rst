
pytest-subprocess
=================

.. image:: https://img.shields.io/pypi/v/pytest-subprocess.svg
    :target: https://pypi.org/project/pytest-subprocess
    :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pytest-subprocess.svg
    :target: https://pypi.org/project/pytest-subprocess
    :alt: Python versions

.. image:: https://codecov.io/gh/aklajnert/pytest-subprocess/branch/master/graph/badge.svg?token=JAU1cGoYL8
  :target: https://codecov.io/gh/aklajnert/pytest-subprocess

.. image:: https://readthedocs.org/projects/pytest-subprocess/badge/?version=latest
   :target: https://pytest-subprocess.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

Pytest plugin to fake subprocess.

.. contents:: :local:

.. include-start

Usage
=====

The plugin adds the ``fake_process`` fixture (and ``fp`` as an alias).
It can be used it to register subprocess results so you won't need to rely on
the real processes. The plugin hooks on the ``subprocess.Popen()``, which is
the base for other subprocess functions. That makes the ``subprocess.run()``,
``subprocess.call()``, ``subprocess.check_call()`` and
``subprocess.check_output()`` methods also functional.

Installation
------------

You can install ``pytest-subprocess`` via `pip`_ from `PyPI`_::

    $ pip install pytest-subprocess


Basic usage
-----------

The most important method is ``fp.register()``
(or ``register_subprocess`` if you prefer to be more verbose), which
allows defining the fake processes behavior.

.. code-block:: python

    def test_echo_null_byte(fp):
        fp.register(["echo", "-ne", "\x00"], stdout=bytes.fromhex("00"))

        process = subprocess.Popen(
            ["echo", "-ne", "\x00"],
            stdout=subprocess.PIPE,
        )
        out, _ = process.communicate()

        assert process.returncode == 0
        assert out == b"\x00"

Optionally, the ``stdout`` and ``stderr`` parameters can be a list (or tuple)
of lines to be joined together with a trailing ``os.linesep`` on each line.

.. code-block:: python

    def test_git(fp):
        fp.register(["git", "branch"], stdout=["* fake_branch", "  master"])

        process = subprocess.Popen(
            ["git", "branch"],
            stdout=subprocess.PIPE,
            universal_newlines=True,
        )
        out, _ = process.communicate()

        assert process.returncode == 0
        assert out == "* fake_branch\n  master\n"

Passing input
-------------

By default, if you use ``input`` argument to the ``Popen.communicate()``
method, it won't crash, but also won't do anything useful. By passing
a function as ``stdin_callable`` argument for the
``fp.register()`` method you can specify the behavior
based on the input. The function shall accept one argument, which will be
the input data. If the function will return a dictionary with ``stdout`` or
``stderr`` keys, its value will be appended to according stream.

.. code-block:: python

    def test_pass_input(fp):
        def stdin_function(input):
            return {
                "stdout": "This input was added: {data}".format(
                    data=input.decode()
                )
            }

        fp.register(
            ["command"],
            stdout=[b"Just stdout"],
            stdin_callable=stdin_function,
        )

        process = subprocess.Popen(
            ["command"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        out, _ = process.communicate(input=b"sample input\n")

        assert out.splitlines() == [
            b"Just stdout",
            b"This input was added: sample input",
        ]

Unregistered commands
---------------------

By default, when the ``fp`` fixture is being used, any attempt to
run subprocess that has not been registered will raise
the ``ProcessNotRegisteredError`` exception. To allow it, use
``fp.allow_unregistered(True)``, which will execute all unregistered
processes with real ``subprocess``, or use
``fp.pass_command("command")`` to allow just a single command.

.. code-block:: python

    def test_real_process(fp):
        with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
            # this will fail, as "ls" command is not registered
            subprocess.call("ls")

        fp.pass_command("ls")
        # now it should be fine
        assert subprocess.call("ls") == 0

        # allow all commands to be called by real subprocess
        fp.allow_unregistered(True)
        assert subprocess.call(["ls", "-l"]) == 0


Differing results
-----------------

Each ``register()`` or ``pass_command()`` method call will register
only one command execution. You can call those methods multiple times, to
change the faked output on each subprocess run. When you call subprocess more
will be raised. To prevent that, call ``fp.keep_last_process(True)``,
which will keep the last registered process forever.

.. code-block:: python

    def test_different_output(fp):
        # register process with output changing each execution
        fp.register("test", stdout="first execution")
        # the second execution will return non-zero exit code
        fp.register("test", stdout="second execution", returncode=1)

        assert subprocess.check_output("test") == b"first execution"
        second_process = subprocess.run("test", stdout=subprocess.PIPE)
        assert second_process.stdout == b"second execution"
        assert second_process.returncode == 1

        # 3rd time shall raise an exception
        with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
            subprocess.check_call("test")

        # now, register two processes once again,
        # but the last one will be kept forever
        fp.register("test", stdout="first execution")
        fp.register("test", stdout="second execution")
        fp.keep_last_process(True)

        # now the processes can be called forever
        assert subprocess.check_output("test") == b"first execution"
        assert subprocess.check_output("test") == b"second execution"
        assert subprocess.check_output("test") == b"second execution"
        assert subprocess.check_output("test") == b"second execution"


Using callbacks
---------------

You can pass a function as ``callback`` argument to the ``register()``
method which will be executed instead of the real subprocess. The callback function
can raise exceptions which will be interpreted in tests as an exception raised
by the subprocess. The fixture will pass ``FakePopen`` class instance into the
callback function, that can be used to change the return code or modify output
streams.

.. code-block:: python

    def callback_function(process):
        process.returncode = 1
        raise PermissionError("exception raised by subprocess")


    def test_raise_exception(fp):
        fp.register(["test"], callback=callback_function)

        with pytest.raises(
            PermissionError, match="exception raised by subprocess"
        ):
            process = subprocess.Popen(["test"])
            process.wait()

        assert process.returncode == 1

It is possible to pass additional keyword arguments into ``callback`` by using
the ``callback_kwargs`` argument:

.. code-block:: python

    def callback_function_with_kwargs(process, return_code):
        process.returncode = return_code


    def test_callback_with_arguments(fp):
        return_code = 127

        fp.register(
            ["test"],
            callback=callback_function_with_kwargs,
            callback_kwargs={"return_code": return_code},
        )

        process = subprocess.Popen(["test"])
        process.wait()

        assert process.returncode == return_code

As a context manager
--------------------

The ``fp`` fixture provides ``context()`` method that allows us to
use it as a context manager. It can be used to limit the scope when a certain
command is allowed, e.g. to make sure that the code doesn't want to execute
it somewhere else.

.. code-block:: python

    def test_context_manager(fp):
        with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
            # command not registered, so will raise an exception
            subprocess.check_call("test")

        with fp.context() as nested_process:
            nested_process.register("test", occurrences=3)
            # now, we can call the command 3 times without error
            assert subprocess.check_call("test") == 0
            assert subprocess.check_call("test") == 0

        # the command was called 2 times, so one occurrence left, but since the
        # context manager has been left, it is not registered anymore
        with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
            subprocess.check_call("test")

Non-exact command matching
--------------------------

If you need to catch a command with some non-predictable elements, like a path
to a randomly-generated file name, you can use ``fake_subprocess.any()`` for
that purpose. The number of arguments that should be matched can be controlled
by ``min`` and ``max`` arguments. To use ``fake_subprocess.any()`` you need
to define the command as a ``tuple`` or ``list``. The matching will work even
if the subprocess command will be called with a string argument.

.. code-block:: python

    def test_non_exact_matching(fp):
        # define a command that will take any number of arguments
        fp.register(["ls", fp.any()])
        assert subprocess.check_call("ls -lah") == 0

        # `fake_subprocess.any()` is OK even with no arguments
        fp.register(["ls", fp.any()])
        assert subprocess.check_call("ls") == 0

        # but it can force a minimum amount of arguments
        fp.register(["cp", fp.any(min=2)])

        with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
            # only one argument is used, so registered command won't match
            subprocess.check_call("cp /source/dir")
        # but two arguments will be fine
        assert subprocess.check_call("cp /source/dir /tmp/random-dir") == 0

        # the `max` argument can be used to limit maximum amount of arguments
        fp.register(["cd", fp.any(max=1)])

        with pytest.raises(fp.exceptions.ProcessNotRegisteredError):
            # cd with two arguments won't match with max=1
            subprocess.check_call("cd ~/ /tmp")
        # but any single argument is fine
        assert subprocess.check_call("cd ~/") == 0

        # `min` and `max` can be used together
        fp.register(["my_app", fp.any(min=1, max=2)])
        assert subprocess.check_call(["my_app", "--help"]) == 0


You can also specify just the command name, and have it match any command with
the same name, regardless of the location. This is accomplished with
``fake_subprocess.program("name")``.

.. code-block:: python

    def test_any_matching_program(fp):
        # define a command that can come from anywhere
        fp.register([fp.program("ls")])
        assert subprocess.check_call("/bin/ls") == 0


Check if process was called
---------------------------

You may want to simply check if a certain command was called, you can do this
by accessing ``fp.calls``, where all commands are stored as-called.
You can also use a utility function ``fp.call_count()`` to see
how many a command has been called. The latter supports ``fp.any()``.

.. code-block:: python

    def test_check_if_called(fp):
        fp.keep_last_process(True)
        # any command can be called
        fp.register([fp.any()])

        subprocess.check_call(["cp", "/tmp/source", "/source"])
        subprocess.check_call(["cp", "/source", "/destination"])
        subprocess.check_call(["cp", "/source", "/other/destination"])

        # you can check if command is in ``fp.calls``
        assert ["cp", "/tmp/source", "/source"] in fp.calls
        assert ["cp", "/source", "/destination"] in fp.calls
        assert ["cp", "/source", "/other/destination"] in fp.calls

        # or check how many it was called, possibly with wildcard arguments
        assert fp.call_count(["cp", "/source", "/destination"]) == 1

        # with ``call_count()`` you don't need to use the same type as
        # the subprocess was called
        assert fp.call_count("cp /tmp/source /source") == 1

        # can be used with ``fp.any()`` to match more calls
        assert fp.call_count(["cp", fp.any()]) == 3


Handling signals
----------------

You can use standard ``kill()``, ``terminate()`` or ``send_signal()`` methods
in ``Popen`` instances. There is an additional ``received_signals()`` method
to get a tuple of all signals received by the process. It is also possible to
set up an optional callback function for signals.

.. code-block:: python

    import signal


    def test_signal_callback(fp):
        """Test that signal callbacks work."""

        def callback(process, sig):
            if sig == signal.SIGTERM:
                process.returncode = -1

        # the `register()` method returns a ProgressRecorder object, where
        # all future matching `Popen()` instances will be appended
        process_recorder = fp.register("test", signal_callback=callback)

        process = subprocess.Popen("test")
        process.send_signal(signal.SIGTERM)
        process.wait()

        assert process.returncode == -1
        assert process.received_signals() == (signal.SIGTERM,)

        # the instance appended to `register()` output is the `Popen` instance
        # created later
        assert process_recorder.first_call is process


Asyncio support
---------------

The plugin now supports asyncio and works for ``asyncio.create_subprocess_shell``
and ``asyncio.create_subprocess_exec``:

.. code-block:: python

    @pytest.mark.asyncio
    async def test_basic_usage(
        fp,
    ):
        fp.register(
            ["some-command-that-is-definitely-unavailable"], returncode=500
        )

        process = await asyncio.create_subprocess_shell(
            "some-command-that-is-definitely-unavailable"
        )
        returncode = await process.wait()

        assert process.returncode == returncode
        assert process.returncode == 500

.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project


.. include-end

Documentation
-------------

For full documentation, including API reference, please see https://pytest-subprocess.readthedocs.io/en/latest/.

Contributing
------------
Contributions are very welcome. Tests can be run with `tox`_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the `MIT`_ license, "pytest-subprocess" is free and open source software


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

----

This `pytest`_ plugin was generated with `Cookiecutter`_ along with `@hackebrot`_'s `cookiecutter-pytest-plugin`_ template.

.. _`Cookiecutter`: https://github.com/audreyr/cookiecutter
.. _`@hackebrot`: https://github.com/hackebrot
.. _`MIT`: http://opensource.org/licenses/MIT
.. _`BSD-3`: http://opensource.org/licenses/BSD-3-Clause
.. _`GNU GPL v3.0`: http://www.gnu.org/licenses/gpl-3.0.txt
.. _`Apache Software License 2.0`: http://www.apache.org/licenses/LICENSE-2.0
.. _`cookiecutter-pytest-plugin`: https://github.com/pytest-dev/cookiecutter-pytest-plugin
.. _`file an issue`: https://github.com/aklajnert/pytest-subprocess/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
