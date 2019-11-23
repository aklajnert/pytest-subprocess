=================
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

A plugin to fake subprocess for pytest

----


Installation
------------

You can install "pytest-subprocess" via `pip`_ from `PyPI`_::

    $ pip install pytest-subprocess


Usage
-----

After plugin installation, the ``fake_subprocess`` fixture will become available. Use it to register
subprocess results so you won't need to rely on the real processes.

Basic usage
===========

The most important method is ``fake_process.register_subprocess()`` which allows to define the fake
processes behavior.

.. code-block:: python

    def test_git(fake_process):
        fake_process.register_subprocess(
            ["git", "branch"], stdout=["* fake_branch", "  master"]
        )

        process = subprocess.Popen(
            ["git", "branch"], stdout=subprocess.PIPE, universal_newlines=True
        )
        out, _ = process.communicate()

        assert process.returncode == 0
        assert out == "* fake_branch\n  master\n"


Unregistered commands
=====================

By default, when the ``fake_process`` fixture is being used, any attempt to run subprocess that has
not been registered will raise the ``ProcessNotRegisteredError`` exception. To allow it, use
``fake_process.allow_unregistered(True)``, which will execute all unregistered processes with
real ``subprocess``, or use ``fake_process.pass_command("command")`` to allow just a single command.

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
=================

Each ``register_subprocess()`` or ``pass_command()`` method call will register only one command
execution. You can call those methods multiple times, to change the faked output on each subprocess
run. When you call subprocess more times than registered command, the ``ProcessNotRegisteredError``
will be raised. To prevent that, call ``fake_process.keep_last_process(True)``, which will keep the
last registered process forever.

.. code-block:: python

    def test_different_output(fake_process):
        # register process with output changing each execution
        fake_process.register_subprocess("test", stdout="first execution")
        # the second execution will return non-zero exit code
        fake_process.register_subprocess("test", stdout="second execution", returncode=1)

        assert subprocess.check_output("test") == b"first execution\n"
        second_process = subprocess.run("test", stdout=subprocess.PIPE)
        assert second_process.stdout == b"second execution\n"
        assert second_process.returncode == 1

        # 3rd time shall raise an exception
        with pytest.raises(pytest_subprocess.ProcessNotRegisteredError):
            subprocess.check_call("test")

        # now, register two processes once again, but the last one will be kept forever
        fake_process.register_subprocess("test", stdout="first execution")
        fake_process.register_subprocess("test", stdout="second execution")
        fake_process.keep_last_process(True)

        # now the processes can be called forever
        assert subprocess.check_output("test") == b"first execution\n"
        assert subprocess.check_output("test") == b"second execution\n"
        assert subprocess.check_output("test") == b"second execution\n"
        assert subprocess.check_output("test") == b"second execution\n"


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
.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
