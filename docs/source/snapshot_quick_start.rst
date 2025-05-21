
1. Atomic Model in pyjevsim
===========================

This document describes how to create a basic DEVS-based Behavior Model using the `pyjevsim` framework.
The example model, PEG (Process Event Generator), receives an external event, processes it for 1 second, 
and outputs a message.

Model Overview
--------------

The PEG model has the following characteristics:

- **Input Port**: ``"start"``
- **Output Port**: ``"process"``
- **States**: ``"Wait"``, ``"Generate"``

To define your own behavior model, you need to inherit from either ``AtomicModel`` or ``BehaviorModel`` 
provided by `pyjevsim`.

Defining State and Port
------------------------

To define the states and ports in your model:

- Use ``init_state(state_name)`` to set the initial state.
- Use ``insert_state(state_name, deadline)`` to add states. The deadline indicates how long the model stays in that state.
- Use ``insert_input_port(port_name)`` to define input ports.
- Use ``insert_output_port(port_name)`` to define output ports.

All names must be strings (``str``).

Main Functions of the DEVS Model
--------------------------------

DEVS models operate based on four core methods:

1. ``ext_trans(self, port, msg)``: Handles external input events and transitions state.
2. ``int_trans(self)``: Handles internal state transitions when a state's deadline is reached.
3. ``output(self, msg_deliver)``: Creates output messages.
4. ``time_advance(self)``: Returns the time duration until the next internal transition.

The table below summarizes key methods used when constructing an AtomicModel based on DEVS formalism,
including descriptions, parameters, and example usages.

+----------------------------+-------------------------------+---------------------------------------------+-----------------------------------------------------+
| Method                     | Description                   | Parameters                                  | Example Usage                                       |
+============================+===============================+=============================================+=====================================================+
| ``init_state(name)``       | Sets the initial state.       | - name: state name (str)                    | ``self.init_state("Idle")``                         |
+----------------------------+-------------------------------+---------------------------------------------+-----------------------------------------------------+
| ``insert_state(name,       | Adds a state and defines its  | - name: state name (str)                    | ``self.insert_state("Run", 3)``                     |
| duration)``                | time advance.                 | - duration: time duration (int or Infinite) |                                                     |
+----------------------------+-------------------------------+---------------------------------------------+-----------------------------------------------------+
| ``insert_input_port(       | Defines an input port to      | - port_name: name of the input port (str)   | ``self.insert_input_port("trigger")``              |
| port_name)``               | receive messages.             |                                             |                                                     |
+----------------------------+-------------------------------+---------------------------------------------+-----------------------------------------------------+
| ``insert_output_port(      | Defines an output port to     | - port_name: name of the output port (str)  | ``self.insert_output_port("done")``                |
| port_name)``               | send messages.                |                                             |                                                     |
+----------------------------+-------------------------------+---------------------------------------------+-----------------------------------------------------+
| ``ext_trans(self, port,    | Handles external events and   | - port: name of input port (str)            | ::                                                  |
| msg)``                     | changes the state accordingly.| - msg: SysMessage object                    |     if port == "start":                             |
|                            |                               |                                             |         self._cur_state = "Run"                     |
+----------------------------+-------------------------------+---------------------------------------------+-----------------------------------------------------+
| ``int_trans(self)``        | Handles internal transitions  | (no parameters)                             | ``self._cur_state = "Wait"``                        |
|                            | to update or keep state.      |                                             |                                                     |
+----------------------------+-------------------------------+---------------------------------------------+-----------------------------------------------------+
| ``output(self,             | Generates and returns an      | - msg_deliver: message deliverer object     | ::                                                  |
| msg_deliver)``             | output message.               |                                             |     msg = SysMessage(self.get_name(), "done")       |
+----------------------------+-------------------------------+---------------------------------------------+-----------------------------------------------------+
| ``time_advance(self)``     | Returns the time advance      | (no parameters)                             | ``return 2`` (e.g., internal event after 2 seconds) |
|                            | for the current state.        |                                             |                                                     |
+----------------------------+-------------------------------+---------------------------------------------+-----------------------------------------------------+

Example PEG Model
-----------------

Below is the complete implementation of the PEG model:

.. code-block:: python

    from pyjevsim.atomic_model import AtomicModel
    from pyjevsim.definition import *
    from pyjevsim.system_message import SysMessage

    class PEG(AtomicModel):
        """Process Event Generator (PEG) class for generating events in a simulation."""

        def __init__(self, name):
            """
            Args:
                name (str): The name of Model
            """
            AtomicModel.__init__(self, name)
            self.init_state("Wait")                 # Initialize initial state
            self.insert_state("Wait", Infinite)     # Add "Wait" state
            self.insert_state("Generate", 1)        # Add "Generate" state

            self.insert_input_port("start")         # Add input port "start"
            self.insert_output_port("process")      # Add output port "process"

            self.msg_no = 0                         # Initialize message number

        def ext_trans(self, port, msg):
            """Handles external transitions based on the input port."""
            if port == "start":
                print(f"[Gen][IN]: started")
                self._cur_state = "Generate"  # Transition state to "Generate"

        def output(self, msg_deliver):
            """Generates the output message when in the "Generate" state."""
            msg = SysMessage(self.get_name(), "process")
            msg.insert(f"{self.msg_no}")  # Insert message number
            print(f"[Gen][OUT]: {self.msg_no}")
            return msg

        def int_trans(self):
            """Handles internal transitions based on the current state."""
            if self._cur_state == "Generate":
                self._cur_state = "Generate"  # Remain in "Generate" state
                self.msg_no += 1  # Increment message number

        def time_advance(self):
            if self._cur_state == "Wait":
                return Infinite
            elif self._cur_state == "Generate":
                return 1
            else:
                return -1

State Transition Flow
----------------------

1. The model starts in the ``"Wait"`` state and waits indefinitely.
2. When it receives a ``"start"`` message, it transitions to the ``"Generate"`` state.
3. In the ``"Generate"`` state, it outputs a message every 1 second.
4. It stays in the ``"Generate"`` state, incrementing the message number with each output.

This example serves as a foundation for building more complex simulation behavior models.

2. Structural Model in pyjevsim
===============================

This section explains how to build a **Structural Model** using `pyjevsim`. A Structural Model allows you to combine
multiple Behavior Models and define message flows between them.

STM Overview
------------

The example Structural Model (`STM`) includes two behavior models:

- ``PEG`` (Process Event Generator): generates messages every 1 second after receiving a "start" signal.
- ``MsgRecv``: receives and processes messages from the PEG model.

**Ports:**

- **Input Port**: ``"start"``
- **Output Port**: ``"output"`` (currently unused)

**Sub-models:**

- ``GEN``: instance of the PEG model
- ``Proc``: instance of MsgRecv

Coupling Structure
------------------

The message flow between the models is defined using coupling relations:

1. External `"start"` input is routed to `PEG`.
2. `PEG` generates `"process"` messages.
3. These messages are routed to `MsgRecv` via its `"recv"` input port.


The following table summarizes key methods used in `StructuralModel` for constructing and connecting sub-models.

+------------------------------+---------------------------------------------------------------+-------------------------------------------------------------+--------------------------------------------------------------+
| Method                       | Description                                                   | Parameters                                                  | Example Usage                                                |
+==============================+===============================================================+=============================================================+==============================================================+
| ``register_entity(model)``   | Registers a Behavior Model as a sub-entity                    | - model: instance of ``AtomicModel`` or ``BehaviorModel``   | ``self.register_entity(peg)``                                |
+------------------------------+---------------------------------------------------------------+-------------------------------------------------------------+--------------------------------------------------------------+
| ``coupling_relation(         | Connects ports between models                                 | - model1: source model                                      | ``self.coupling_relation(self, "start", peg, "start")``      |
| model1, port1, model2,       |                                                               | - port1: source port name (str)                             | ``self.coupling_relation(peg, "process", proc, "recv")``     |
| port2)``                     |                                                               | - model2: destination model                                 |                                                              |
|                              |                                                               | - port2: destination port name (str)                        |                                                              |
+------------------------------+---------------------------------------------------------------+-------------------------------------------------------------+--------------------------------------------------------------+


Code Example
------------

.. code-block:: python

    from pyjevsim.structural_model import StructuralModel
    from .model_peg import PEG
    from .model_msg_recv import MsgRecv

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
-----------

- ``insert_input_port()``, ``insert_output_port()`` define STM's interaction with the external system.
- ``register_entity()`` adds sub-models to the STM structure.
- ``coupling_relation()`` connects ports between models or between STM and its sub-models.

This basic structural model can be extended with more sub-models, hierarchical composition, or dynamic scheduling
for complex simulations.

3. Simulation Engine(SystemExecutor) in pyjevsim
================================================

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
-----------------------

1. **Create Executor**: Initialize `SysExecutor` with time resolution and execution mode.
2. **Define Ports**: Add top-level input ports using `insert_input_port()`.
3. **Register Models**: Register structural or behavior models with `register_entity()`.
4. **Define Coupling**: Set up inter-model and external coupling with `coupling_relation()`.
5. **Inject Events**: Insert initial events via `insert_external_event()`.
6. **Run Simulation**: Use `simulate(t)` in a loop or scheduler.

.. code-block:: python

    from pyjevsim.definition import *
    from pyjevsim.system_executor import SysExecutor

    from .model_msg_recv import MsgRecv
    from .model_peg import PEG
    from .model_stm import STM

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

This engine orchestrates all time progression, message passing, and model coordination in the simulation system.
