Pyjevsim Quick Start
====================

1. Atomic Model in pyjevsim
---------------------------

This quick start builds a DEVS ``BehaviorModel`` with pyjevsim. The example,
PEG (Process Event Generator), starts after an external event and emits one
message per simulated second.

Atomic Model Overview
~~~~~~~~~~~~~~~~~~~~~

PEG has one input port, one output port, and two states:

- **Input Port**: ``"start"``
- **Output Port**: ``"process"``
- **States**: ``"Wait"``, ``"Generate"``

User-defined models inherit from ``AtomicModel`` or ``BehaviorModel``.

Defining State and Port
~~~~~~~~~~~~~~~~~~~~~~~

Declare states and ports in the constructor:

- Use ``init_state(state_name)`` to set the initial state.
- Use ``insert_state(state_name, deadline)`` to add states. The deadline indicates how long the model stays in that state.
- Use ``insert_input_port(port_name)`` to define input ports.
- Use ``insert_output_port(port_name)`` to define output ports.

All names must be strings (``str``).

Main Functions of the DEVS Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DEVS models implement three transition/output methods:

1. ``ext_trans(self, port, msg)``: Handles external input events and transitions state.
2. ``int_trans(self)``: Handles internal state transitions when a state's deadline is reached.
3. ``output(self, msg_deliver)``: Creates output messages and adds them to the ``msg_deliver`` bag via ``msg_deliver.insert_message(msg)``.

The executor reads the current state's duration from the value registered by
``insert_state(name, duration)``. It does not call a model-defined
``time_advance()`` method.

The methods used by the example are listed below.

.. list-table:: BehaviorModel / AtomicModel API Summary
   :widths: 25 35 40
   :header-rows: 1

   * - Method
     - Description
     - Parameters
   * - ``init_state(name)``
     - Sets the initial state
     - - ``name`` (str): state name
   * - ``insert_state(name, duration)``
     - Adds a state and defines its time advance
     - - ``name`` (str): state name  
       - ``duration`` (int or ``Infinite``): time duration
   * - ``insert_input_port(port_name)``
     - Defines an input port to receive messages
     - - ``port_name`` (str): name of the input port
   * - ``insert_output_port(port_name)``
     - Defines an output port to send messages
     - - ``port_name`` (str): name of the output port
   * - ``ext_trans(self, port, msg)``
     - Handles external events and changes state accordingly
     - - ``port`` (str): input port name  
       - ``msg``: SysMessage object
   * - ``int_trans(self)``
     - Handles internal transitions to update or keep the state
     - (no parameters)
   * - ``output(self, msg_deliver)``
     - Builds output messages and adds them to ``msg_deliver`` via ``insert_message(msg)`` (v2.0 two-phase tick reads the bag, not the return value)
     - - ``msg_deliver`` (``MessageDeliverer``): the bag to deposit outputs into

Example PEG Model
~~~~~~~~~~~~~~~~~

The complete PEG model is:

.. code-block:: python

    from pyjevsim.atomic_model import AtomicModel
    from pyjevsim.definition import *
    from pyjevsim.system_message import SysMessage

    class PEG(AtomicModel):
        """Emit numbered process messages after a start event."""

        def __init__(self, name):
            """Create a PEG named *name*."""
            AtomicModel.__init__(self, name)
            self.init_state("Wait")
            self.insert_state("Wait", Infinite)
            self.insert_state("Generate", 1)

            self.insert_input_port("start")
            self.insert_output_port("process")

            self.msg_no = 0

        def ext_trans(self, port, msg):
            if port == "start":
                print(f"[Gen][IN]: started")
                self._cur_state = "Generate"

        def output(self, msg_deliver):
            msg = SysMessage(self.get_name(), "process")
            msg.insert(f"{self.msg_no}")
            print(f"[Gen][OUT]: {self.msg_no}")
            msg_deliver.insert_message(msg)

        def int_trans(self):
            if self._cur_state == "Generate":
                self._cur_state = "Generate"
                self.msg_no += 1

State Transition Flow
~~~~~~~~~~~~~~~~~~~~~

1. The model starts in the ``"Wait"`` state and waits indefinitely.
2. When it receives a ``"start"`` message, it transitions to the ``"Generate"`` state.
3. In the ``"Generate"`` state, it outputs a message every 1 second.
4. It stays in the ``"Generate"`` state, incrementing the message number with each output.

Debugging Uncaught Output Messages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, output messages emitted on a port with **no downstream
coupling** are dropped silently. To inspect them while debugging a
model graph, pass ``track_uncaught=True`` to the executor:

.. code-block:: python

   se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, track_uncaught=True)

The simulator's ``DefaultMessageCatcher``, available as ``se.dmc``, then
receives each uncoupled message on its ``"uncaught"`` input port. Each captured
message invokes the catcher's external transition and reschedules it, so this
mode adds work for every uncoupled output. Enable it only when that information
is needed.

Output Messages Are Shared by Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a model's output port has multiple downstream subscribers, every
subscriber receives the **same** ``SysMessage`` object. ``pyjevsim`` does
not deep-copy outputs during propagation.

The practical rule for modelers:

- Treat received messages as **immutable**.
- If your model needs to mutate a payload, copy it on the receiver side
  first, e.g. ``payload = list(msg.retrieve())``.

``benchmark/aliasing_test.py`` records the behavior for the engine versions
available when the test is run.

2. Structural Model in pyjevsim
-------------------------------

A **Structural Model** groups behavior models and defines the message paths
between their ports.

Structural Overview
~~~~~~~~~~~~~~~~~~~

The example ``STM`` contains two behavior models:

- ``PEG`` (Process Event Generator): generates messages every 1 second after receiving a "start" signal.
- ``MsgRecv``: receives and processes messages from the PEG model.

**Ports:**

- **Input Port**: ``"start"``
- **Output Port**: ``"output"`` (currently unused)

**Sub-models:**

- ``GEN``: instance of the PEG model
- ``Proc``: instance of MsgRecv

Coupling Structure
~~~~~~~~~~~~~~~~~~

The message flow between the models is defined using coupling relations:

1. External `"start"` input is routed to `PEG`.
2. `PEG` generates `"process"` messages.
3. These messages are routed to `MsgRecv` via its `"recv"` input port.


The following ``StructuralModel`` methods register and connect sub-models.

.. list-table:: StructuralModel API Summary
   :widths: 30 35 35
   :header-rows: 1

   * - Method
     - Description
     - Parameters
   * - ``register_entity(model)``
     - Registers a Behavior Model as a sub-entity
     - - ``model``: instance of ``AtomicModel`` or ``BehaviorModel``
   * - ``coupling_relation(model1, port1, model2, port2)``
     - Connects ports between models
     - - ``model1``: source model  
       - ``port1``: source port name (str)  
       - ``model2``: destination model  
       - ``port2``: destination port name (str)


Code Example
~~~~~~~~~~~~

This condensed example uses the model files in the repository's ``tests``
package. The package-qualified imports work when the command is run from the
repository root.

.. code-block:: python

    from pyjevsim.structural_model import StructuralModel
    from tests.model_peg import PEG
    from tests.model_msg_recv import MsgRecv

    class STM(StructuralModel):
        def __init__(self, name):
            super().__init__(name)

            self.insert_input_port("start")
            self.insert_output_port("output")

            # Model Creation
            peg = PEG("GEN")  # PEG Model (Behavior Model)
            proc = MsgRecv("Proc")

            # Register Models
            self.register_entity(peg)
            self.register_entity(proc)

            # Define Coupling
            self.coupling_relation(self, "start", peg, "start")
            self.coupling_relation(peg, "process", proc, "recv")

Explanation
~~~~~~~~~~~~

- ``insert_input_port()``, ``insert_output_port()`` define STM's interaction with the external system.
- ``register_entity()`` adds sub-models to the STM structure.
- ``coupling_relation()`` connects ports between models or between STM and its sub-models.

3. Simulation Engine(SystemExecutor) in pyjevsim
------------------------------------------------

The System Executor (`SysExecutor`) is the simulation engine that executes DEVS models in `pyjevsim`.  
It manages simulation time, model registration, external events, and inter-model communication.

.. list-table:: SysExecutor Methods and Constructor
   :widths: 30 20 50
   :header-rows: 1

   * - Method / Constructor
     - Description
     - Parameters
   * - ``SysExecutor(_time_resolution, _sim_name="default", ex_mode=ExecutionType.V_TIME, snapshot_manager=None)``
     - Initializes the simulation engine
     - - ``_time_resolution`` (float): Time step size  
       - ``_sim_name`` (str): Simulation name  
       - ``ex_mode``: Execution type  
       - ``snapshot_manager``: optional
   * - ``insert_input_port(port_name)``
     - Adds an input port
     - ``port_name`` (str): Name of the port
   * - ``register_entity(model, inst_t=0)``
     - Registers a behavior or structural model
     - - ``model``: an AtomicModel or StructuralModel  
       - ``inst_t`` (float): instantiation time
   * - ``coupling_relation(source_model, source_port, dest_model, dest_port)``
     - Connects ports between models
     - - ``source_model`` and ``dest_model``  
       - ``source_port`` and ``dest_port`` (str)
   * - ``insert_external_event(port_name, value)``
     - Schedules an external input event
     - ``port_name`` (str), ``value`` (any)
   * - ``simulate(duration)``
     - Runs the simulation for a given time
     - ``duration`` (float)

Simulation Flow Example
~~~~~~~~~~~~~~~~~~~~~~~

1. **Create Executor**: Initialize `SysExecutor` with time resolution and execution mode.
2. **Define Ports**: Add top-level input ports using `insert_input_port()`.
3. **Register Models**: Register structural or behavior models with `register_entity()`.
4. **Define Coupling**: Set up inter-model and external coupling with `coupling_relation()`.
5. **Inject Events**: Insert initial events via `insert_external_event()`.
6. **Run Simulation**: Use `simulate(t)` in a loop or scheduler.

.. code-block:: python

    from pyjevsim.definition import *
    from pyjevsim.system_executor import SysExecutor

    from tests.model_msg_recv import MsgRecv
    from tests.model_peg import PEG
    from tests.model_stm import STM

    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME)

    se.insert_input_port("start")

    # Register Structural Model
    gen = STM("Gen")
    se.register_entity(gen, inst_t=3)

    # Register Behavior Model
    peg = PEG("GEN")
    se.register_entity(peg)

    # Connect models
    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(se, "start", peg, "start")

    # Schedule input event
    se.insert_external_event("start", None)

    # Run simulation
    for _ in range(5):
        se.simulate(1)

The repository checks this hierarchy with:

.. code-block:: console

   $ python -m pytest -q tests/test_hierarchical.py

4. Two-Phase Tick and Confluent Transitions
-------------------------------------------

Starting in 2.0, ``SysExecutor`` runs each simulated instant as a
**two-phase tick**:

1. **Phase A — output.** Every model whose deadline has been reached
   evaluates ``output()`` against its *pre-transition* state. Outputs
   are buffered, not delivered yet.
2. **Phase B — transitions.** The buffered outputs are routed through
   the coupling graph, then each affected model runs the appropriate
   transition: ``int_trans`` (imminent only), ``ext_trans`` (receiver
   only), or ``con_trans`` (both at once).

When a model is both imminent and receiving an external event at the same
instant, the second phase invokes ``con_trans`` once.

Overriding ``con_trans``
~~~~~~~~~~~~~~~~~~~~~~~~

The default ``con_trans`` runs ``δ_int ; δ_ext`` (internal then external),
matching xdevs.py and PythonPDEVS. Override it on your ``BehaviorModel``
subclass when you need different confluent semantics:

.. code-block:: python

    class PriorityModel(BehaviorModel):
        def con_trans(self, port_msgs):
            # ext-then-int: incoming events take precedence over the
            # scheduled internal transition.
            for port, msg in port_msgs:
                self.ext_trans(port, msg)
            self.int_trans()

``port_msgs`` is an iterable of ``(port_name, SysMessage)`` tuples
delivered at this instant.

5. HLA Stepped Execution
------------------------

For HLA federate integration (IEEE 1516-2010 RTI), pyjevsim exposes a
**stepped** execution API in addition to ``simulate()``. The federate
ambassador owns the main loop and asks pyjevsim to advance up to a
granted time:

.. code-block:: python

    from pyjevsim.definition import ExecutionType
    from pyjevsim.system_executor import SysExecutor

    se = SysExecutor(1, ex_mode=ExecutionType.HLA_TIME)
    # ... register entities, set up coupling ...

    while not federate.done:
        next_t = se.get_next_event_time()        # for Time Advance Request
        granted = federate.request_advance(next_t)  # RTI grants time
        outputs = se.step(granted)                  # run cascade up to granted
        federate.publish(outputs)

Two methods drive the integration:

- ``get_next_event_time()`` — returns the next scheduled internal or
  external event time (or ``Infinite``). The federate uses this as its
  Time Advance Request value.
- ``step(granted_time)`` — processes every event whose ``req_time`` is
  ``<= granted_time`` using the same two-phase tick. Cascading
  ``sigma=0`` transitions are run within the same call; events past the
  grant stay in the FEL for the next ``step()``. Returns a deque of
  output events generated during this grant.

Use ``ExecutionType.HLA_TIME`` so the executor does not also try to
own time advancement internally.
