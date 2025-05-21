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
