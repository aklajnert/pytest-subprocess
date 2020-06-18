History
=======

unreleased (2020-06-18)  
-----------------------

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
