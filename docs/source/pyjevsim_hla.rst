HLA / RTI Integration
=====================

pyjevsim runs ordinary DEVS models as HLA (IEEE 1516-2010) federates. The
model code stays pure DEVS; what changes is the *factory* that wraps each
model and the *transport* (RTI backend) it talks to. The same model runs
unchanged in a standalone simulation, on the in-process test bus, or
against a live RTI such as Pitch pRTI.

Architecture
------------

::

   BehaviorModel (pure DEVS)
        |  output()/ext_trans() on named ports
        v
   HLAExecutor ---- intercepts bound ports ----> RTIConnector.send(...)
        ^                                              |  codec.encode -> _do_send
        |  insert_external_event                       v
   _HLARouter <---- _emit(kind, fom_id, ...) ---- backend RX thread
        |
        v
   SysExecutor.step(granted)  <-- Federate.run_until --> request_time_advance

Four replaceable pieces live in ``pyjevsim.hla``:

``RTIConnector``
   Base class for RTI backends. A backend implements only the
   RTI-specific hooks; the common plumbing is inherited.
``Codec`` / ``IdentityCodec``
   FOM (de)serialization, decoupled from the wire transport.
``RTICapabilities``
   Feature flags a backend advertises (time management, TSO, object
   attributes, ...).
registry
   ``register_rti`` / ``create_rti`` / ``available_rtis`` select a
   backend by name.

Built-in backends
-----------------

.. list-table::
   :header-rows: 1
   :widths: 18 42 40

   * - Name
     - Use
     - Dependency
   * - ``loopback``
     - self-mirror, single-federate unit tests
     - none
   * - ``inprocess``
     - multi-federate in-process bus (tests/demos)
     - none
   * - ``pitch``
     - Pitch pRTI (IEEE 1516-2010), live federation
     - ``pip install pyjevsim[hla-pitch]`` + Java >= 9 + a running CRC

Turning a model into a federate
-------------------------------

.. code-block:: python

   from pyjevsim import SysExecutor, ExecutionType
   from pyjevsim.hla import (
       create_rti, HLAExecutorFactory, HLAInteraction, HLAAttribute, Federate,
   )

   # 1. Declare bindings: model port -> FOM identifier.
   bindings = {
       "out_msg": HLAInteraction("Comm.ChatMsg", direction="out"),
       "in_msg":  HLAInteraction("Comm.ChatMsg", direction="in"),
   }

   # 2. Pick a transport by name (models are backend-agnostic).
   transport = create_rti("inprocess")          # or "pitch", ...

   # 3. Wire the HLA factory and register the model.
   sys_exec = SysExecutor(1, ex_mode=ExecutionType.HLA_TIME)
   sys_exec.exec_factory = HLAExecutorFactory(transport, {"chatter": bindings})
   sys_exec.register_entity(my_model)           # my_model.get_name() == "chatter"

   # 4. Drive the federate.
   fed = Federate(sys_exec, transport)
   fed.join("MyFederation", "chatter", fom_paths=["Comm.xml"])
   fed.publish(bindings["out_msg"])
   fed.subscribe(bindings["in_msg"])
   fed.run_until(end_time=60.0, lookahead=1.0)
   fed.resign()

Object attributes use ``HLAAttribute`` instead of ``HLAInteraction``;
an outbound attribute additionally needs ``object_class``.

Adding a new RTI backend
------------------------

Subclass ``RTIConnector`` and implement the two abstract hooks (plus any
lifecycle hooks the RTI needs); call ``_emit`` from the receive path:

.. code-block:: python

   from pyjevsim.hla import RTIConnector, RTICapabilities, register_rti

   class MyRTI(RTIConnector):
       capabilities = RTICapabilities(name="myrti", time_management=True,
                                      timestamp_ordered=True)

       def _do_send(self, binding, wire, timestamp):
           ...  # ship to the RTI (sendInteraction / updateAttributeValues)

       def _do_request_time_advance(self, target):
           ...  # block until granted; return the granted logical time

       # optional: _do_join / _do_publish / _do_subscribe / _do_resign / _do_close
       # inbound: from your RX thread call self._emit(kind, fom_id, wire, timestamp)

   register_rti("myrti", lambda **kw: MyRTI(**kw))

The connector supplies direction enforcement, ``codec`` encode/decode,
single-callback dispatch, the join/resign state machine, and idempotent
close. Full guide: ``docs/hla/rti_interface.md`` in the repository.

Ping-pong example
-----------------

``examples/hla_pingpong/`` contains two federates (``ping`` / ``pong``)
that rally a ball via interactions while synchronizing an object
attribute. Run it offline (no Java)::

   python examples/hla_pingpong/run_inprocess.py

or against a live Pitch pRTI (``pitch`` backend, with a CRC running)::

   python examples/hla_pingpong/run_pitch.py

Anti-torpedo co-simulation (hla_atsim)
--------------------------------------

``examples/hla_atsim/`` is a larger, verification-driven example: it splits
the ``examples/atsim`` anti-torpedo scenario into **two federates**
(surfaceship + torpedo). In the standalone ``atsim`` the platforms sense one
another through a shared global registry; the HLA version replaces that with
**HLA object attributes** — each federate publishes its own hull and decoy
positions and reflects the peer's into a per-federate one-tick position
snapshot that the detectors read from (bidirectional sensing requires
``lookahead = 1``).

The example ships two decoy scenarios, ``self_propelled`` (default) and
``stationary`` (select with ``PYJEVSIM_SCENARIO`` or a CLI argument), and a
gate that proves the federated run reproduces a single-executor reference
**byte-for-byte** for both::

   python examples/hla_atsim/verify_equivalence.py
   # -> MATCH self_propelled: 180 rows
   # -> MATCH stationary: 180 rows

The same trajectories are produced by the single-process reference
(``run_standalone_headless.py``), the two-federate in-process bus
(``run_hla_inprocess.py``), and two federates over a live Pitch pRTI
(``run_hla_pitch.py``) — identical in every case. This demonstrates that the
RTI-mediated position exchange faithfully reproduces the monolithic
simulation's dynamics.

.. figure:: ../../examples/hla_atsim/figures/atsim_self_propelled.png
   :width: 70%
   :align: center

   Self-propelled decoy engagement (top-down x-y, 30 ticks): the surfaceship
   (blue) flees while its launcher deploys decoys (green); one seduces the
   torpedo (red), which locks onto the decoy and stops short of the ship.

.. figure:: ../../examples/hla_atsim/figures/atsim_stationary.png
   :width: 70%
   :align: center

   Stationary decoy engagement: the decoys hold fixed offsets away from the
   torpedo's approach, so the torpedo is not seduced and runs down the ship's
   track. Both figures are rendered by ``plot_trajectories.py`` and are
   identical for the standalone and the two-federate HLA runs.

``plot_trajectories.py`` also renders a 3-D (x, y, z-depth) view and a
range-vs-tick plot per scenario. The range plot makes the decoy effectiveness
quantitative — the torpedo's 3-D distance to the ship and to each decoy over
time:

.. figure:: ../../examples/hla_atsim/figures/atsim_self_propelled_range.png
   :width: 70%
   :align: center

   Self-propelled decoys: the torpedo→decoy distance collapses to zero around
   tick 13 (seduction) while the torpedo→ship distance grows past 70 — the ship
   escapes.

.. figure:: ../../examples/hla_atsim/figures/atsim_stationary_range.png
   :width: 70%
   :align: center

   Stationary decoys: no decoy holds the torpedo; its distance to the ship
   instead closes to ~6 and holds. The full figure set (top-down, 3-D, range
   for both scenarios) is under ``examples/hla_atsim/figures/``.

Low-level stepping
------------------

To embed pyjevsim in your own federate ambassador instead of using a
backend, drive ``HLA_TIME`` mode directly:

.. code-block:: python

   se = SysExecutor(1, ex_mode=ExecutionType.HLA_TIME)
   se.register_entity(model)
   se.init_sim()
   while not se.is_terminated():
       next_t = se.get_next_event_time()          # compute Time Advance Request
       granted = ...                              # wait for the RTI grant
       output_events = se.step(granted)           # process events <= granted
       # ... publish output_events to the RTI ...

``step(granted_time)`` runs the same two-phase Parallel-DEVS tick as the
V_TIME path (correct ``int`` / ``ext`` / ``con`` transitions, multi-round
sigma=0 cascades in one call) and returns the output events drained
during the grant. This is exactly what the ``pitch`` backend uses
internally.
