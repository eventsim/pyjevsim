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