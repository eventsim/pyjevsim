
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