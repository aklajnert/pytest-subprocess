pytest-subprocess
=================

.. image:: https://img.shields.io/pypi/v/pytest-subprocess.svg
    :target: https://pypi.org/project/pytest-subprocess
    :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pytest-subprocess.svg
    :target: https://pypi.org/project/pytest-subprocess
    :alt: Python versions

.. image:: https://dev.azure.com/aklajnert/pytest-subprocess/_apis/build/status/aklajnert.pytest-subprocess?branchName=master
    :target: https://dev.azure.com/aklajnert/pytest-subprocess/_build/latest?definitionId=6&branchName=master
    :alt: See Build Status on Azure Pipelines

.. image:: https://codecov.io/gh/aklajnert/pytest-subprocess/branch/master/graph/badge.svg?token=JAU1cGoYL8
  :target: https://codecov.io/gh/aklajnert/pytest-subprocess

.. image:: https://readthedocs.org/projects/pytest-subprocess/badge/?version=latest
   :target: https://pytest-subprocess.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

A plugin to fake subprocess for pytest

.. contents:: :local:

.. include-start

Usage
=====

The plugin adds the ``fake_subprocess`` fixture. It can be used it to register
subprocess results so you won't need to rely on the real processes. The plugin
hooks on the ``subprocess.Popen()``, which is the base for other subprocess
functions. That makes the ``subprocess.run()``, ``subprocess.call()``,
``subprocess.check_call()`` and ``subprocess.check_output()`` methods
also functional.

Installation
------------

You can install ``pytest-subprocess`` via `pip`_ from `PyPI`_::

    $ pip install pytest-subprocess


Basic usage
-----------

The most important method is ``fake_process.register_subprocess()`` which
allows defining the fake processes behavior.

.. code-block:: python

    def test_git(fake_process):
        fake_process.register_subprocess(
            ["git", "branch"], stdout=["* fake_branch", "  master"]
        )

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
``fake_process.register_subprocess()`` method you can specify the behavior
based on the input. The function shall accept one argument, which will be
the input data. If the function will return a dictionary with ``stdout`` or
``stderr`` keys, its value will be appended to according stream.

.. code-block:: python

    def test_pass_input(fake_process):
        def stdin_function(input):
            return {
                "stdout": "This input was added: {data}".format(
                    data=input.decode()
                )
            }

        fake_process.register_subprocess(
            ["command"],
            stdout=[b"Just stdout"],
            stdin_callable=stdin_function,
        )

        process = subprocess.Popen(
            ["command"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        )
        out, _ = process.communicate(input=b"sample input")

        assert out.splitlines() == [
            b"Just stdout",
            b"This input was added: sample input",
        ]

Unregistered commands
---------------------

By default, when the ``fake_process`` fixture is being used, any attempt to
run subprocess that has not been registered will raise
the ``ProcessNotRegisteredError`` exception. To allow it, use
``fake_process.allow_unregistered(True)``, which will execute all unregistered
processes with real ``subprocess``, or use
``fake_process.pass_command("command")`` to allow just a single command.

.. code-block:: python

    def test_real_process(fake_process):
        with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
            # this will fail, as "ls" command is not registered
            subprocess.call("ls")

        fake_process.pass_command("ls")
        # now it should be fine
        assert subprocess.call("ls") == 0

        # allow all commands to be called by real subprocess
        fake_process.allow_unregistered(True)
        assert subprocess.call(["ls", "-l"]) == 0


Differing results
-----------------

Each ``register_subprocess()`` or ``pass_command()`` method call will register
only one command execution. You can call those methods multiple times, to
change the faked output on each subprocess run. When you call subprocess more
will be raised. To prevent that, call ``fake_process.keep_last_process(True)``,
which will keep the last registered process forever.

.. code-block:: python

    def test_different_output(fake_process):
        # register process with output changing each execution
        fake_process.register_subprocess("test", stdout="first execution")
        # the second execution will return non-zero exit code
        fake_process.register_subprocess(
            "test", stdout="second execution", returncode=1
        )

        assert subprocess.check_output("test") == b"first execution\n"
        second_process = subprocess.run("test", stdout=subprocess.PIPE)
        assert second_process.stdout == b"second execution\n"
        assert second_process.returncode == 1

        # 3rd time shall raise an exception
        with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
            subprocess.check_call("test")

        # now, register two processes once again,
        # but the last one will be kept forever
        fake_process.register_subprocess("test", stdout="first execution")
        fake_process.register_subprocess("test", stdout="second execution")
        fake_process.keep_last_process(True)

        # now the processes can be called forever
        assert subprocess.check_output("test") == b"first execution\n"
        assert subprocess.check_output("test") == b"second execution\n"
        assert subprocess.check_output("test") == b"second execution\n"
        assert subprocess.check_output("test") == b"second execution\n"


Using callbacks
---------------

You can pass a function as ``callback`` argument to the ``register_subprocess()``
method which will be executed instead of the real subprocess. The callback function
can raise exceptions which will be interpreted in tests as an exception raised
by the subprocess. The fixture will pass ``FakePopen`` class instance into the
callback function, that can be used to change the return code or modify output
streams.

.. code-block:: python

    def callback_function(process):
        process.returncode = 1
        raise PermissionError("exception raised by subprocess")


    def test_raise_exception(fake_process):
        fake_process.register_subprocess(["test"], callback=callback_function)

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


    def test_callback_with_arguments(fake_process):
        return_code = 127

        fake_process.register_subprocess(
            ["test"],
            callback=callback_function_with_kwargs,
            callback_kwargs={"return_code": return_code},
        )

        process = subprocess.Popen(["test"])
        process.wait()

        assert process.returncode == return_code

As a context manager
--------------------

The ``fake_process`` fixture provides ``context()`` method that allows us to
use it as a context manager. It can be used to limit the scope when a certain
command is allowed, e.g. to make sure that the code doesn't want to execute
it somewhere else.

.. code-block:: python

    def test_context_manager(fake_process):
        with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
            # command not registered, so will raise an exception
            subprocess.check_call("test")

        with fake_process.context() as nested_process:
            nested_process.register_subprocess("test", occurrences=3)
            # now, we can call the command 3 times without error
            assert subprocess.check_call("test") == 0
            assert subprocess.check_call("test") == 0

        # the command was called 2 times, so one occurrence left, but since the
        # context manager has been left, it is not registered anymore
        with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
            subprocess.check_call("test")

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
