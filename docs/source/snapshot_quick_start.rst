Snapshot and Restore Quick Start
================================

pyjevsim has two snapshot workflows:

- A **simulation snapshot** saves the registered models and their coupling
  relations. Use it when you want to reconstruct a model configuration later.
- A **model snapshot** saves one behavior or structural model when a condition
  is met. Use it to branch a run from selected model state.

Snapshot files are written with ``dill``. The Python modules that define the
models must therefore remain importable when a snapshot is restored.

.. warning::

   Loading a ``dill`` file can execute Python code. Restore snapshots only from
   sources you trust.

Save a simulation
-----------------

Create one :class:`~pyjevsim.snapshot_manager.SnapshotManager` and pass it to
the :class:`~pyjevsim.system_executor.SysExecutor` constructor. Register the
models and couplings as usual, then call ``snapshot_simulation`` at the point
where you want to save them.

The example below shows the snapshot-specific parts of a two-model setup. See
:doc:`pyjevsim_quick_start` for complete behavior-model and coupling examples.

.. code-block:: python

   from pyjevsim.definition import ExecutionType
   from pyjevsim.snapshot_manager import SnapshotManager
   from pyjevsim.system_executor import SysExecutor

   snapshots = SnapshotManager()
   sim = SysExecutor(
       1,
       _sim_name="experiment",
       ex_mode=ExecutionType.V_TIME,
       snapshot_manager=snapshots,
   )

   # Construct and register your models before starting the run.
   sim.register_entity(generator)
   sim.register_entity(receiver)
   sim.coupling_relation(generator, "process", receiver, "recv")

   sim.simulate(10)
   sim.snapshot_simulation(
       name="checkpoint",
       directory_path="./snapshot",
   )

This call creates ``snapshot/checkpoint`` with the following files:

.. code-block:: text

   snapshot/checkpoint/
   |-- relation_map.json
   |-- model_map.json
   |-- dc.simx
   |-- generator-name.simx
   `-- receiver-name.simx

There is one ``.simx`` file for each entry in the executor's model map,
including the built-in default message catcher ``dc``. Give registered models
unique names so that they can be restored and coupled unambiguously.

Restore a simulation
--------------------

Construct a :class:`~pyjevsim.restore_handler.RestoreHandler` with the same
snapshot name and parent directory. ``SnapshotManager.get_engine()`` reads the
saved models and relations and returns the reconstructed executor.

.. code-block:: python

   from pyjevsim.definition import ExecutionType
   from pyjevsim.restore_handler import RestoreHandler
   from pyjevsim.snapshot_manager import SnapshotManager

   restore = RestoreHandler(
       t_resol=1,
       ex_mode=ExecutionType.V_TIME,
       name="checkpoint",
       path="./snapshot",
   )
   snapshots = SnapshotManager(restore_handler=restore)
   sim = snapshots.get_engine()

   # Recreate executor-level inputs before injecting new events.
   sim.insert_input_port("start")
   sim.insert_external_event("start", None)
   sim.simulate(10)

``get_engine()`` already creates and populates a ``SysExecutor``; do not create
a second executor for the restored models.

What the simulation snapshot contains
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The restored executor contains the serialized model objects and their saved
coupling relations. It does not resume the original Python process. In
particular, the current executor time, pending external events, output-event
queue, callbacks, and executor-level input/output port declarations are not
stored. The restored executor starts at simulation time zero.

After restoring, recreate any top-level ports and events that the next part of
the run needs. Reconnect resources outside pyjevsim, such as files, sockets, or
RTI sessions, in application code as well.

Run the BankSim example
-----------------------

The BankSim example includes a complete simulation-level save and restore.
From ``examples/banksim``, first save the run at virtual time ``100``:

.. code-block:: console

   $ python banksim_snapshot.py 100 20

The command writes ``snapshot/banksim``. The second argument is the generator
count used by the what-if branch. Restore that directory with:

.. code-block:: console

   $ python banksim_restore.py 100 20

The restore script rebuilds the executor and applies the example's
generator-count branch before continuing. See :doc:`banksim_sim` for all
BankSim variants.

Save one model when a condition is met
--------------------------------------

For a model snapshot, subclass
:class:`~pyjevsim.snapshot_condition.SnapshotCondition`. The following
condition saves ``Gen`` the first time its request time reaches 10 or later:

.. code-block:: python

   from pyjevsim.snapshot_condition import SnapshotCondition

   class SaveGenOnce(SnapshotCondition):
       @staticmethod
       def create_executor(behavior_executor):
           return SaveGenOnce(behavior_executor)

       def __init__(self, behavior_executor):
           super().__init__(behavior_executor)
           self.saved = False

       def snapshot_time_condition(self, global_time):
           if not self.saved and global_time >= 10:
               self.saved = True
               return True
           return False

The base class returns ``False`` for the transition and output hooks, so this
condition responds only to time. Register the condition under the exact model
name before registering that model with the executor:

.. code-block:: python

   from pyjevsim.definition import ExecutionType
   from pyjevsim.snapshot_manager import SnapshotManager
   from pyjevsim.system_executor import SysExecutor

   snapshots = SnapshotManager()
   snapshots.register_snapshot_condition("Gen", SaveGenOnce.create_executor)

   sim = SysExecutor(
       1,
       ex_mode=ExecutionType.V_TIME,
       snapshot_manager=snapshots,
   )
   sim.register_entity(generator)  # generator.get_name() must be "Gen"

When the condition returns ``True``, pyjevsim writes
``snapshot/[time]Gen.simx``. Conditions are also available immediately before
and after external transitions, internal transitions, and output calls; those
files use prefixes such as ``[ext_before]`` and ``[output_after]``.

Restore one model
-----------------

``SnapshotManager.load_snapshot`` deserializes a model snapshot. The optional
name argument lets you assign the restored model a new name for a branch run.

.. code-block:: python

   from pathlib import Path

   from pyjevsim.restore_handler import RestoreHandler
   from pyjevsim.snapshot_manager import SnapshotManager

   snapshots = SnapshotManager(restore_handler=RestoreHandler())
   payload = Path("snapshot/[time]Gen.simx").read_bytes()
   restored_gen = snapshots.load_snapshot("GenBranch", payload)

   branch_sim.register_entity(restored_gen)

A model snapshot does not include the rest of the executor or its couplings.
Register the restored model with a new or existing executor, then add the
other models and coupling relations required by the branch.
