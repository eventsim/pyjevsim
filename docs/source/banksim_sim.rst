BankSim Execution Variants
==========================

The BankSim scripts are command-line entry points rather than importable API
modules. Run them from ``examples/banksim`` so that they can read
``scenario.yaml`` and write snapshot data in the expected location.

Classic simulation
------------------

``banksim_classic.py`` runs the queueing model without snapshot support. It
takes the virtual time for the what-if change and the replacement number of
customer generators as positional arguments.

.. code-block:: console

   $ python banksim_classic.py 100 20

See :download:`banksim_classic.py <../../examples/banksim/banksim_classic.py>`.

Model snapshot and restore
--------------------------

``banksim_model_snapshot.py`` saves a customer-generator model during a run.
Run ``banksim_model_restore.py`` afterward to start a simulation with that
saved model.

.. code-block:: console

   $ python banksim_model_snapshot.py 100 20
   $ python banksim_model_restore.py 100 20

See :download:`banksim_model_snapshot.py <../../examples/banksim/banksim_model_snapshot.py>`
and :download:`banksim_model_restore.py <../../examples/banksim/banksim_model_restore.py>`.

Simulation snapshot and restore
-------------------------------

``banksim_snapshot.py`` saves the simulation models and their coupling
relations. Run ``banksim_restore.py`` afterward to continue from that saved
simulation.

.. code-block:: console

   $ python banksim_snapshot.py 100 20
   $ python banksim_restore.py 100 20

See :download:`banksim_snapshot.py <../../examples/banksim/banksim_snapshot.py>`
and :download:`banksim_restore.py <../../examples/banksim/banksim_restore.py>`.
