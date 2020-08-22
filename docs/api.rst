API Reference
=============

fake_subprocess
---------------

The main entrypoint class for all ``fake_subprocess`` operations is the
``FakeProcess`` class. This class is instantiated and returned when the
``fake_subprocess`` fixture is being used.

.. autoclass:: pytest_subprocess.core.FakeProcess
   :members:

any()
-----

For a non-exact matching, you can use the ``Any()`` class that is available to
use via ``fake_subprocess.any``. This class can be used to replace a number
of arguments that might occur,

.. autoclass:: pytest_subprocess.utils.Any
   :members:
