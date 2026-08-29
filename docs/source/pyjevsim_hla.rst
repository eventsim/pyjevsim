HLA / RTI Integration
=====================

pyjevsim wraps port-compatible DEVS models as HLA (IEEE 1516-2010) federates.
Model classes need not contain RTI API calls; the surrounding *factory*, port
bindings, FOM mapping, launch configuration, and *transport* (RTI backend)
provide the federation integration. A compatible model class can therefore be
used with the in-process test bus or a supported live RTI such as Pitch pRTI,
Portico, or the experimental GORTI adapter.

The repository's `HLA validation and reproducibility guide
<https://github.com/eventsim/pyjevsim/tree/main/docs/hla-validation>`_
defines the comparison procedure and provides reference traces, service
coverage, and limitations.

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

The backend interface contains four parts:

``RTIConnector``
   Base class for RTI backends. Two methods are the minimum abstract surface;
   a live adapter also supplies lifecycle, declaration, and receive hooks.
   Direction checks, codec dispatch, callback registration, and lifecycle
   state handling are inherited.
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
     - ``python -m pip install "pyjevsim[hla-java]"`` + Java >= 11 + a running CRC
   * - ``portico``
     - Portico (open source, IEEE 1516-2010), live federation
     - ``python -m pip install "pyjevsim[hla-java]"`` + Java >= 11 + ``portico.jar``
   * - ``gorti``
     - experimental GORTI native-Python IEEE 1516-2010 client
     - ``python -m pip install -e C:\path\to\gorti\pysdk`` + a reachable ``rtid``

The Pitch and Portico backends use the ``hla.rti1516e`` Java API discovered
through ``RtiFactoryFactory``. The backend name, RTI jar, JVM, FOM map, and
launch settings select the concrete Java RTI.
:class:`~pyjevsim.hla.backends.portico.PorticoTransport` subclasses the Pitch
adapter and handles Portico's ``HLAunicodeString`` representation and
receive-order reflections. Its tick barrier depends on documented
``quiet``/``settle`` waits; see the validation guide.
The ``gorti`` backend uses GORTI's native ``rti1516e`` Python SDK, without
Java or JPype. The SDK is not published on PyPI, so install it from its source
checkout with ``python -m pip install -e C:\path\to\gorti\pysdk``.
Recorded AT/SIM checks cover object registration/discovery, six-attribute
update/reflection, and regulating/constrained logical time. They do
not establish release-grade GORTI support, complete HLA Object Management, or
formal IEEE 1516 conformance.

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

   # 2. Pick a transport by name; selection stays outside the model class.
   transport = create_rti("inprocess")          # or "pitch", "portico", "gorti"

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

Object attributes use ``HLAAttribute`` instead of ``HLAInteraction``.
``object_class`` is an optional hint for custom transports; the built-in live
adapters resolve the class from their FOM map.

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

or against the open-source Portico RTI (``portico`` backend, no CRC)::

   set RTI_HOME=C:\path\to\portico-2.1.4
   python examples/hla_pingpong/run_portico.py

Anti-torpedo co-simulation (hla_atsim)
--------------------------------------

``examples/hla_atsim/`` splits
the ``examples/atsim`` anti-torpedo scenario into **two federates**
(surfaceship + torpedo). In the standalone ``atsim`` the platforms sense one
another through a shared global registry; the HLA version replaces that with
**HLA object attributes** — each federate publishes its own hull and decoy
positions and reflects peer positions into a per-federate snapshot that the
detectors read on the following caller tick. The driver grant increment and
default outbound timestamp offset are one caller tick. Portico's internal
regulating lookahead is one RTI sub-step, or one third of a caller tick.
Pitch and GORTI map caller time 1:1 to RTI logical time.

The example ships two decoy scenarios, ``self_propelled`` (default) and
``stationary`` (select with ``PYJEVSIM_SCENARIO`` or a CLI argument), and a
comparison that checks the federated run against a single-executor reference
with exact equality of sorted, ``%.10g``-formatted application-state rows for
both scenarios::

   python examples/hla_atsim/verify_equivalence.py
   # -> MATCH self_propelled: 180 rows
   # -> MATCH stationary: 180 rows

Recorded checks found the same reference rows for the single-process run
(``run_standalone_headless.py``), the two-federate in-process run
(``run_hla_inprocess.py``), Pitch pRTI (``run_hla_pitch.py``), and Portico
(``run_hla_portico.py``), and a pre-release functional qualification of GORTI
(``run_hla_gorti.py``). This comparison is limited to application-visible
state at each recorded tick.
``verify_equivalence_rti.py`` compares a
selected live RTI against the committed reference and fails when the external
toolchain does not produce a trace::

   set PYJEVSIM_RTI=portico
   set PYJEVSIM_JAR=C:\path\to\portico-2.1.4\lib\portico.jar
   python examples/hla_atsim/verify_equivalence_rti.py
   # -> MATCH self_propelled: 180 canonical rows (portico vs committed reference)
   # -> MATCH stationary: 180 canonical rows (portico vs committed reference)

For GORTI, source-install its SDK and either set ``GORTI_URL`` for an existing
service or point ``GORTI_RTID`` at a local service binary::

   python -m pip install -e C:\path\to\gorti\pysdk
   set GORTI_RTID=C:\path\to\rtid.exe
   set PYJEVSIM_RTI=gorti
   python examples/hla_atsim/verify_equivalence_rti.py
   # -> MATCH self_propelled: 180 canonical rows (gorti vs reference)
   # -> MATCH stationary: 180 canonical rows (gorti vs reference)

.. figure:: ../../examples/hla_atsim/figures/atsim_self_propelled.png
   :width: 70%
   :align: center

   Self-propelled decoy scenario (top-down x-y, 30 ticks). The ship is blue,
   decoys are green, and the torpedo is red.

.. figure:: ../../examples/hla_atsim/figures/atsim_stationary.png
   :width: 70%
   :align: center

   Stationary decoy scenario. The decoys hold their drop positions while the
   torpedo continues toward the ship's track. ``plot_trajectories.py`` renders
   both figures from the reference rows.

``plot_trajectories.py`` also renders a 3-D (x, y, z-depth) view and a
range-vs-tick plot showing the torpedo's 3-D distance to the ship and each
decoy:

.. figure:: ../../examples/hla_atsim/figures/atsim_self_propelled_range.png
   :width: 70%
   :align: center

   Self-propelled decoys: the torpedo-to-decoy distance reaches zero around
   tick 13 while the torpedo-to-ship distance grows past 70.

.. figure:: ../../examples/hla_atsim/figures/atsim_stationary_range.png
   :width: 70%
   :align: center

   Stationary decoys: the torpedo-to-ship distance approaches about 6 and then
   remains there. The complete figure set is under
   ``examples/hla_atsim/figures/``.

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
       granted = rti.request_time_advance(next_t) # wait for the RTI grant
       output_events = se.step(granted)           # process events <= granted
       # ... publish output_events to the RTI ...

``step(granted_time)`` runs the same two-phase Parallel-DEVS tick as the
V_TIME path (``int`` / ``ext`` / ``con`` selection and multi-round sigma=0
cascades in one call) and returns the output events drained
during the grant. This is the core path used by the ``pitch`` backend, its
``portico`` subclass, and the experimental native ``gorti`` backend.
