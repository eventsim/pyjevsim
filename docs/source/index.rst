.. pyjevsim documentation master file, created by
   sphinx-quickstart on Fri Sep 20 10:40:52 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PyJEvSim documentation
======================

PyJEvSim is a DEVS (Discrete Event System Specification) modeling and
simulation environment with built-in journaling. It supports snapshot and
restore of individual models or the full simulation engine, virtual-time
and real-time execution, and HLA (IEEE 1516-2010) federate integration
with pluggable RTI backends (including Pitch pRTI).

  - GitHub: `eventsim/pyjevsim <https://github.com/eventsim/pyjevsim>`_
  - PyPI: `pyjevsim <https://pypi.org/project/pyjevsim/>`_

What's new in 2.1
-----------------

- **Pluggable RTI backends.** A new ``RTIConnector`` interface
  (``pyjevsim.hla``) lets any RTI drive a pyjevsim federate without
  touching model code. A backend implements just ``_do_send`` and
  ``_do_request_time_advance``; direction enforcement, FOM codec,
  callback dispatch and the join/resign state machine are inherited.
  Ships an in-process bus (``inprocess``) and a **Pitch pRTI**
  (IEEE 1516-2010) backend (``pitch``, via JPype). Select by name with
  ``create_rti(...)``. See :doc:`pyjevsim_hla`.
- **HLA ping-pong example** under ``examples/hla_pingpong/``: two
  federates exchanging interactions and synchronizing an object
  attribute, runnable offline or against a live RTI.
- **Unified DEVS tick.** ``V_TIME``, ``R_TIME`` and ``HLA_TIME`` share a
  single two-phase tick body, so external events get correct confluent
  (``con_trans``) semantics on every path.

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
   pyjevsim_hla
