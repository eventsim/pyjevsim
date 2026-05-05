.. pyjevsim documentation master file, created by
   sphinx-quickstart on Fri Sep 20 10:40:52 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PyJEvSim documentation
======================

PyJEvSim is a DEVS (Discrete Event System Specification) modeling and
simulation environment with built-in journaling. It supports snapshot and
restore of individual models or the full simulation engine, virtual-time
and real-time execution, and an HLA-friendly stepped execution mode for
federate integration.

  - GitHub: `eventsim/pyjevsim <https://github.com/eventsim/pyjevsim>`_
  - PyPI: `pyjevsim <https://pypi.org/project/pyjevsim/>`_

What's new in 2.0
-----------------

Version 2.0 changes the core simulation tick and adds federate-friendly
APIs. Existing models do not need to change, but the observable event
ordering at simultaneous-event boundaries does.

- **Two-phase tick.** ``SysExecutor`` now runs every due model's
  ``output()`` first, then the corresponding ``ext_trans`` /
  ``int_trans`` / ``con_trans``. This fixes confluent-event ordering
  under Parallel-DEVS semantics. See :doc:`pyjevsim_quick_start`.
- **HLA stepped execution.** ``SysExecutor.step(granted_time)`` and
  ``get_next_event_time()`` let an HLA federate ambassador drive
  pyjevsim under an IEEE 1516-2010 RTI without owning the main loop.
- **V_TIME jump-to-next-event.** The virtual-time scheduler now hops
  directly to the next scheduled event instead of advancing by a fixed
  ``time_resolution``, eliminating idle ticks in sparse models.
- **Opt-in uncaught-message tracking.** Pass ``track_uncaught=True`` to
  ``SysExecutor`` to route messages on uncoupled output ports to
  ``DefaultMessageCatcher`` for debugging.
- **DEVStone benchmark suite** under ``benchmark/`` with cross-engine
  comparison adapters; see :doc:`benchmark`.

Installing PyJEvSim
-------------------

From PyPI (recommended):

.. code-block:: console

   $ pip install pyjevsim

From source:

.. code-block:: console

   $ git clone https://github.com/eventsim/pyjevsim
   $ cd pyjevsim
   $ pip install -e .

Requirements
------------

- Python >= 3.10
- ``dill >= 0.3.6`` (installed automatically)

PyJEvSim Components
-------------------

.. toctree::
   :maxdepth: 2

   modules

Quick Start Guides
------------------

.. toctree::
   :maxdepth: 1

   pyjevsim_quick_start
   snapshot_quick_start
