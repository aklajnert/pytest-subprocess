.. pytest-subprocess documentation master file, created by
   sphinx-quickstart on Sat Nov 23 13:49:07 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

pytest-subprocess
=================

This is a pytest plugin to fake the real subprocess behavior to make your tests more independent.

Example
-------

You can use the provided ``fake_process`` fixture to register commands and specify
their behavior before they will be executed. This will prevent a real subprocess
execution.

.. code-block:: python

    def test_process(fake_process):
        fake_process.register_subprocess(["fake-command"])
        process = subprocess.run(["fake-command"])

        assert process.returncode == 0


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   usage
   api
   history



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
