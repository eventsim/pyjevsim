PyJEvSim documentation
======================

PyJEvSim is a DEVS (Discrete Event System Specification) modeling and
simulation environment with built-in journaling. It supports snapshot and
restore of individual models or the full simulation engine, virtual-time
and real-time execution, and HLA (IEEE 1516-2010) federate integration
with pluggable RTI backends. Version 2.2.0 includes adapters for Pitch pRTI
and the open-source Portico RTI, plus an experimental GORTI adapter.

  - GitHub: `eventsim/pyjevsim <https://github.com/eventsim/pyjevsim>`_
  - PyPI: `pyjevsim <https://pypi.org/project/pyjevsim/>`_

Changes in 2.2
--------------

- **Portico backend.** The live HLA adapter now supports Portico 2.1.4 in
  addition to Pitch pRTI.
- **Experimental GORTI backend.** Selected interaction, object-attribute, and
  logical-time paths use a source-installed GORTI SDK and separately built
  ``rtid``. The recorded checks are not release-grade GORTI support, complete
  HLA Object Management, or formal IEEE 1516 conformance.
- **AT/SIM reference data.** The two-federate AT/SIM example provides two
  30-tick scenarios, complete 180-row reference trajectories, and offline and
  optional live-RTI comparison commands.
- **HLA design and service documentation.** Architecture, logical-time
  behavior, the implemented IEEE 1516 service subset, related projects, and
  limitations are documented alongside the code.
- **Direction checks and failure reporting.** Binding directions are checked at runtime, and
  the live AT/SIM runner reports missing peer data, worker failures, and
  verifier timeouts.

What's new in 2.1
-----------------

- **Pluggable RTI backends.** A new ``RTIConnector`` interface
  (``pyjevsim.hla``) defines the extension boundary through which an RTI can
  drive a pyjevsim federate without embedding RTI calls in model code. A
  minimal backend implements ``_do_send`` and
  ``_do_request_time_advance``; a live HLA adapter also supplies lifecycle,
  declaration, and receive hooks. Direction enforcement, FOM codec,
  callback dispatch and the join/resign state machine are inherited.
  Ships an in-process bus (``inprocess``) and a **Pitch pRTI**
  (IEEE 1516-2010) backend (``pitch``, via JPype). Select by name with
  ``create_rti(...)``. See :doc:`pyjevsim_hla`.
- **HLA ping-pong example** under ``examples/hla_pingpong/``: two
  federates exchanging interactions and synchronizing an object
  attribute, runnable offline or against a live RTI.
- **Unified DEVS tick.** ``V_TIME``, ``R_TIME`` and ``HLA_TIME`` share a
  single two-phase tick body. An imminent model with input at the same
  simulated instant uses ``con_trans`` in each mode.

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

From PyPI:

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

Developer and Maintainer Guides
-------------------------------

The source repository keeps contributor, security, release, and detailed HLA
guides next to the code they describe:

.. toctree::
   :maxdepth: 1

   Contributing <https://github.com/eventsim/pyjevsim/blob/main/CONTRIBUTING.md>
   Security policy <https://github.com/eventsim/pyjevsim/blob/main/SECURITY.md>
   HLA developer guide <https://github.com/eventsim/pyjevsim/blob/main/docs/hla/instruction.md>
   RTI backend interface <https://github.com/eventsim/pyjevsim/blob/main/docs/hla/rti_interface.md>
   HLA validation and reproducibility <https://github.com/eventsim/pyjevsim/blob/main/docs/hla-validation/README.md>
   Release checklist <https://github.com/eventsim/pyjevsim/blob/main/docs/releasing.md>
