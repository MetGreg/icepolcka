.. _Testing:

Testing
=======
To quickly test if the package works for you as expected, go to the 'icepolcka_utils' package
folder:

.. code-block::

    cd icepolcka_utils


and start the tests with

.. code-block::

    make coverage

This will execute all unittests located in the 'tests' sub-folder. In case a test fails, it will
tell you the reason. If everything works, it will give you a summary about the percentage of the
package code that was executed by the tests. In that case everything should work as expected.