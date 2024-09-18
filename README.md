<a id="pyjevsim"></a>

# pyjevsim

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.behavior_executor"></a>

# pyjevsim.behavior\_executor

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.behavior_executor.BehaviorExecutor"></a>

## BehaviorExecutor Objects

```python
class BehaviorExecutor(Executor)
```

<a id="pyjevsim.behavior_executor.BehaviorExecutor.__init__"></a>

#### \_\_init\_\_

```python
def __init__(itime=Infinite,
             dtime=Infinite,
             ename="default",
             behavior_model=None)
```

A decorated form of the BehaviorModel, ready to be executed by the SysExecutor.
Manages the simulation time of the BehaviorModel and the information in the SysExecutor.

**Arguments**:

- `itime` _int or Infinite_ - Time of instance creation
- `dtime` _int or Infinite_ - Time of instance destruction
- `ename` _str_ - SysExecutor name
- `behavior_model` _ModelType.BEHAVIORAL_ - Behavior Model

<a id="pyjevsim.behavior_executor.BehaviorExecutor.set_global_time"></a>

#### set\_global\_time

```python
def set_global_time(gtime)
```

Sets the global time for the executor and behavior model

<a id="pyjevsim.behavior_executor.BehaviorExecutor.get_core_model"></a>

#### get\_core\_model

```python
def get_core_model()
```

Returns the core behavior model

<a id="pyjevsim.behavior_executor.BehaviorExecutor.__str__"></a>

#### \_\_str\_\_

```python
def __str__()
```

Returns a string representation of the executor

<a id="pyjevsim.behavior_executor.BehaviorExecutor.get_name"></a>

#### get\_name

```python
def get_name()
```

Returns the name of the behavior model

<a id="pyjevsim.behavior_executor.BehaviorExecutor.get_engine_name"></a>

#### get\_engine\_name

```python
def get_engine_name()
```

Returns the name of the engine

<a id="pyjevsim.behavior_executor.BehaviorExecutor.set_engine_name"></a>

#### set\_engine\_name

```python
def set_engine_name(engine_name)
```

Sets the name of the engine

<a id="pyjevsim.behavior_executor.BehaviorExecutor.get_create_time"></a>

#### get\_create\_time

```python
def get_create_time()
```

Returns the instance creation time

<a id="pyjevsim.behavior_executor.BehaviorExecutor.get_destruct_time"></a>

#### get\_destruct\_time

```python
def get_destruct_time()
```

Returns the destruction time

<a id="pyjevsim.behavior_executor.BehaviorExecutor.get_obj_id"></a>

#### get\_obj\_id

```python
def get_obj_id()
```

Returns the object ID of the behavior model

<a id="pyjevsim.behavior_executor.BehaviorExecutor.get_cur_state"></a>

#### get\_cur\_state

```python
def get_cur_state()
```

Returns the current state of the executor

<a id="pyjevsim.behavior_executor.BehaviorExecutor.init_state"></a>

#### init\_state

```python
def init_state(state)
```

Initializes the state of the executor

<a id="pyjevsim.behavior_executor.BehaviorExecutor.ext_trans"></a>

#### ext\_trans

```python
def ext_trans(port, msg)
```

Handles external transition based on port and message

<a id="pyjevsim.behavior_executor.BehaviorExecutor.int_trans"></a>

#### int\_trans

```python
def int_trans()
```

Handles internal transition

<a id="pyjevsim.behavior_executor.BehaviorExecutor.output"></a>

#### output

```python
def output()
```

Executes the output function of the behavior model

<a id="pyjevsim.behavior_executor.BehaviorExecutor.time_advance"></a>

#### time\_advance

```python
def time_advance()
```

Returns the time advance value for the current state

<a id="pyjevsim.behavior_executor.BehaviorExecutor.set_req_time"></a>

#### set\_req\_time

```python
def set_req_time(global_time)
```

Sets the request time based on the global time and time advance

<a id="pyjevsim.behavior_executor.BehaviorExecutor.get_req_time"></a>

#### get\_req\_time

```python
def get_req_time()
```

Returns the request time and resets the cancel flag if necessary

<a id="pyjevsim.behavior_model"></a>

# pyjevsim.behavior\_model

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.behavior_model.BehaviorModel"></a>

## BehaviorModel Objects

```python
class BehaviorModel(CoreModel)
```

BehaviorModel template to inherit when constructing a new Model.

<a id="pyjevsim.behavior_model.BehaviorModel.__init__"></a>

#### \_\_init\_\_

```python
def __init__(_name="")
```

**Arguments**:

- `_name` _str_ - Unique model name

<a id="pyjevsim.behavior_model.BehaviorModel.insert_state"></a>

#### insert\_state

```python
def insert_state(name, deadline="inf")
```

Insert "state" into the BehaviorModel

**Arguments**:

- `name` _str_ - State name
- `deadline` _str or Infinite_ - Time until the state is active. Defaults to Infinite.

<a id="pyjevsim.behavior_model.BehaviorModel.update_state"></a>

#### update\_state

```python
def update_state(name, deadline="inf")
```

Updates an existing state in the BehaviorModel

**Arguments**:

- `name` _str_ - state name to update
- `deadline` _str or Infinite_ - Time until the state is active. Defaults to Infinite.

<a id="pyjevsim.behavior_model.BehaviorModel.cancel_rescheduling"></a>

#### cancel\_rescheduling

```python
def cancel_rescheduling()
```

Canceled scheduling

<a id="pyjevsim.behavior_model.BehaviorModel.init_state"></a>

#### init\_state

```python
def init_state(state)
```

Sets the initial state

**Arguments**:

- `state` _str_ - Initial state name

<a id="pyjevsim.behavior_model.BehaviorModel.set_global_time"></a>

#### set\_global\_time

```python
def set_global_time(gtime)
```

Set gloabl time

**Arguments**:

- `gtime` _float_ - Global time

<a id="pyjevsim.behavior_model.BehaviorModel.ext_trans"></a>

#### ext\_trans

```python
@abstractmethod
def ext_trans(port, msg)
```

Defines the external transition, to be implemented by subclasses

<a id="pyjevsim.behavior_model.BehaviorModel.int_trans"></a>

#### int\_trans

```python
@abstractmethod
def int_trans()
```

Defines the internal transition, to be implemented by subclasses

<a id="pyjevsim.behavior_model.BehaviorModel.output"></a>

#### output

```python
@abstractmethod
def output()
```

Defines the output function, to be implemented by subclasses

<a id="pyjevsim.behavior_model.BehaviorModel.get_cancel_flag"></a>

#### get\_cancel\_flag

```python
def get_cancel_flag()
```

Returns the cancel reschedule flag

<a id="pyjevsim.behavior_model.BehaviorModel.reset_cancel_flag"></a>

#### reset\_cancel\_flag

```python
def reset_cancel_flag()
```

Resets the cancel reschedule flag to False

<a id="pyjevsim.behavior_model.BehaviorModel.retrieve_states"></a>

#### retrieve\_states

```python
def retrieve_states()
```

Returns the states dictionary

<a id="pyjevsim.behavior_model.BehaviorModel.find_state"></a>

#### find\_state

```python
def find_state(name)
```

Checks if a state exists

**Arguments**:

- `name` _str_ - State name
  

**Returns**:

- `bool` - True if state exists, False otherwise

<a id="pyjevsim.behavior_model.BehaviorModel.insert_external_transition"></a>

#### insert\_external\_transition

```python
def insert_external_transition(pre_state, event, post_state)
```

Inserts an external transition

**Arguments**:

- `pre_state` _str_ - Previous state
- `event` _str_ - Event causing the transition
- `post_state` _str_ - Next state

<a id="pyjevsim.behavior_model.BehaviorModel.retrieve_external_transition"></a>

#### retrieve\_external\_transition

```python
def retrieve_external_transition(pre_state)
```

Retrieves external transitions for a given state

**Arguments**:

- `pre_state` _str_ - Previous state
  

**Returns**:

- `list` - List of external transitions

<a id="pyjevsim.behavior_model.BehaviorModel.retrieve_next_external_state"></a>

#### retrieve\_next\_external\_state

```python
def retrieve_next_external_state(pre_state, event)
```

Retrieves the next state for a given external transition

**Arguments**:

- `pre_state` _str_ - Previous state
- `event` _str_ - Event causing the transition
  

**Returns**:

- `str` - Next state

<a id="pyjevsim.behavior_model.BehaviorModel.find_external_transition"></a>

#### find\_external\_transition

```python
def find_external_transition(pre_state)
```

Checks if there are external transitions for a given state

**Arguments**:

- `pre_state` _str_ - Previous state
  

**Returns**:

- `bool` - True if transitions exist, False otherwise

<a id="pyjevsim.behavior_model.BehaviorModel.insert_internal_transition"></a>

#### insert\_internal\_transition

```python
def insert_internal_transition(pre_state, event, post_state)
```

Inserts an internal transition

**Arguments**:

- `pre_state` _str_ - Previous state
- `event` _str_ - Event causing the transition
- `post_state` _str_ - Next state

<a id="pyjevsim.behavior_model.BehaviorModel.retrieve_internal_transition"></a>

#### retrieve\_internal\_transition

```python
def retrieve_internal_transition(pre_state)
```

Retrieves internal transitions for a given state

**Arguments**:

- `pre_state` _str_ - Previous state
  

**Returns**:

- `list` - List of internal transitions

<a id="pyjevsim.behavior_model.BehaviorModel.retrieve_next_internal_state"></a>

#### retrieve\_next\_internal\_state

```python
def retrieve_next_internal_state(pre_state, event)
```

Retrieves the next state for a given internal transition

**Arguments**:

- `pre_state` _str_ - Previous state
- `event` _str_ - Event causing the transition
  

**Returns**:

- `str` - Next state

<a id="pyjevsim.behavior_model.BehaviorModel.find_internal_transition"></a>

#### find\_internal\_transition

```python
def find_internal_transition(pre_state)
```

Checks if there are internal transitions for a given state

**Arguments**:

- `pre_state` _str_ - Previous state
  

**Returns**:

- `bool` - True if transitions exist, False otherwise

<a id="pyjevsim.behavior_model.BehaviorModel.serialize"></a>

#### serialize

```python
def serialize()
```

Serializes the behavior model to a JSON object

**Returns**:

- `OrderedDict` - Serialized JSON object

<a id="pyjevsim.behavior_model.BehaviorModel.deserialize"></a>

#### deserialize

```python
def deserialize(json)
```

Deserializes the behavior model from a JSON object

**Arguments**:

- `json` _dict_ - JSON object containing the model data

<a id="pyjevsim.behavior_model_executor"></a>

# pyjevsim.behavior\_model\_executor

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.behavior_model_executor.BehaviorModelExecutor"></a>

## BehaviorModelExecutor Objects

```python
class BehaviorModelExecutor(BehaviorExecutor)
```

Allows the use of models from DEVS Module “pyevsim” via the decorator technique.

<a id="pyjevsim.behavior_model_executor.BehaviorModelExecutor.__init__"></a>

#### \_\_init\_\_

```python
def __init__(itime=Infinite,
             dtime=Infinite,
             ename="default",
             behavior_model="")
```

**Arguments**:

- `itime` _int or Infinite_ - Time of instance creation
- `dtime` _int or Infinite_ - Time of instance destruction
- `ename` _str_ - SysExecutor name
- `behavior_model` _ModelType.BEHAVIORAL_ - Behavior Model

<a id="pyjevsim.core_model"></a>

# pyjevsim.core\_model

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.core_model.CoreModel"></a>

## CoreModel Objects

```python
class CoreModel(SystemObject)
```

All forms of Models in Pyjevsim have a CoreModel as their foundation. 
CoreModel class serves as a base model with basic functionalities for input and output ports.

<a id="pyjevsim.core_model.CoreModel.__init__"></a>

#### \_\_init\_\_

```python
def __init__(_name, _type)
```

**Arguments**:

- `_name` _str_ - Model name
- `_type` _ModelType.BEHAVIORAL or ModelType.STRUCTURAL or ModelType.UTILITY_ - Model type

<a id="pyjevsim.core_model.CoreModel.set_name"></a>

#### set\_name

```python
def set_name(_name)
```

Sets the name of the model.

**Arguments**:

- `_name` _str_ - New name of the model

<a id="pyjevsim.core_model.CoreModel.get_name"></a>

#### get\_name

```python
def get_name()
```

Returns the name of the model.

**Returns**:

- `str` - Name of the model

<a id="pyjevsim.core_model.CoreModel.get_model_type"></a>

#### get\_model\_type

```python
def get_model_type()
```

Returns the type of the model.

**Returns**:

  (ModelType.BEHAVIORAL or ModelType.STRUCTURAL or ModelType.UTILITY) : Type of the model

<a id="pyjevsim.core_model.CoreModel.insert_input_port"></a>

#### insert\_input\_port

```python
def insert_input_port(port)
```

Inserts an input port to the model.

**Arguments**:

- `port` _str_ - Name of the input port

<a id="pyjevsim.core_model.CoreModel.retrieve_input_ports"></a>

#### retrieve\_input\_ports

```python
def retrieve_input_ports()
```

Retrieves all input ports of the model.

**Returns**:

- `list` - List of input ports

<a id="pyjevsim.core_model.CoreModel.insert_output_port"></a>

#### insert\_output\_port

```python
def insert_output_port(port)
```

Inserts an output port to the model.

**Arguments**:

- `port` _str_ - Name of the output port

<a id="pyjevsim.core_model.CoreModel.retrieve_output_ports"></a>

#### retrieve\_output\_ports

```python
def retrieve_output_ports()
```

Retrieves all output ports of the model.

**Returns**:

- `list` - List of output ports

<a id="pyjevsim.core_model.CoreModel.model_snapshot"></a>

#### model\_snapshot

```python
def model_snapshot()
```

Snapshot the information of the running model.

**Returns**:

- `dict` - Dictionary containing model type, model name, and model data

<a id="pyjevsim.default_message_catcher"></a>

# pyjevsim.default\_message\_catcher

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.default_message_catcher.DefaultMessageCatcher"></a>

## DefaultMessageCatcher Objects

```python
class DefaultMessageCatcher(BehaviorModel)
```

A default model for catching uncaught messages.
Receiving and not processing uncaught messages

<a id="pyjevsim.default_message_catcher.DefaultMessageCatcher.ext_trans"></a>

#### ext\_trans

```python
def ext_trans(port, msg)
```

Received an uncaught message.

**Arguments**:

- `port` _str_ - The port name
- `msg` _SysMessage_ - The incoming message

<a id="pyjevsim.definition"></a>

# pyjevsim.definition

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.definition.AttributeType"></a>

## AttributeType Objects

```python
class AttributeType(Enum)
```

Enum for attribute types.

<a id="pyjevsim.definition.AttributeType.resolve_type_from_str"></a>

#### resolve\_type\_from\_str

```python
@staticmethod
def resolve_type_from_str(name)
```

Resolves an attribute type from a string.

**Arguments**:

- `name` _str_ - The name of the attribute type

**Returns**:

- `AttributeType` - The resolved attribute type

<a id="pyjevsim.definition.AttributeType.resolve_type_from_enum"></a>

#### resolve\_type\_from\_enum

```python
@staticmethod
def resolve_type_from_enum(enum)
```

Resolves an attribute type to a string.

**Arguments**:

- `enum` _AttributeType_ - The attribute type enum

**Returns**:

- `str` - The name of the attribute type

<a id="pyjevsim.definition.SimulationMode"></a>

## SimulationMode Objects

```python
class SimulationMode(Enum)
```

Enum for simulation modes.

<a id="pyjevsim.definition.SimulationMode.SIMULATION_RUNNING"></a>

#### SIMULATION\_RUNNING

Simulation Engine is instantiated, simulation is running

<a id="pyjevsim.definition.SimulationMode.SIMULATION_PAUSE"></a>

#### SIMULATION\_PAUSE

Simulation Engine is instantiated, simulation paused

<a id="pyjevsim.definition.SimulationMode.SIMULATION_UNKNOWN"></a>

#### SIMULATION\_UNKNOWN

Simulation Engine went to abnormal state

<a id="pyjevsim.definition.ModelType"></a>

## ModelType Objects

```python
class ModelType(Enum)
```

Enum for model types.

<a id="pyjevsim.definition.ModelType.BEHAVIORAL"></a>

#### BEHAVIORAL

BehaviorModel type : DEVS Atomic Model

<a id="pyjevsim.definition.ModelType.STRUCTURAL"></a>

#### STRUCTURAL

StructuralModel type : DEVS Coupled Model

<a id="pyjevsim.definition.ExecutionType"></a>

## ExecutionType Objects

```python
class ExecutionType(Enum)
```

Enum for execution types.

<a id="pyjevsim.definition.ExecutionType.R_TIME"></a>

#### R\_TIME

Real time

<a id="pyjevsim.definition.ExecutionType.V_TIME"></a>

#### V\_TIME

Virtual time

<a id="pyjevsim.definition.SingletonType"></a>

## SingletonType Objects

```python
class SingletonType(object)
```

A decorator for making a class a singleton.

<a id="pyjevsim.definition.SingletonType.__call__"></a>

#### \_\_call\_\_

```python
def __call__(cls, *args, **kwargs)
```

Creates or returns the singleton instance of the class.

**Arguments**:

- `cls` _type_ - The class to be instantiated
- `*args` - Variable length argument list
- `**kwargs` - Arbitrary keyword arguments
  

**Returns**:

- `object` - The singleton instance of the class

<a id="pyjevsim.executor"></a>

# pyjevsim.executor

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.executor.Executor"></a>

## Executor Objects

```python
class Executor()
```

Base class for executors.

<a id="pyjevsim.executor.Executor.__init__"></a>

#### \_\_init\_\_

```python
def __init__(itime, dtime, ename)
```

**Arguments**:

- `itime` _float_ - Instance creation time
- `dtime` _float_ - Destruction time
- `ename` _str_ - Engine name

<a id="pyjevsim.executor_factory"></a>

# pyjevsim.executor\_factory

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.executor_factory.ExecutorFactory"></a>

## ExecutorFactory Objects

```python
class ExecutorFactory()
```

Factory class to create different types of executors.

<a id="pyjevsim.executor_factory.ExecutorFactory.create_executor"></a>

#### create\_executor

```python
def create_executor(global_time, ins_t, des_t, en_name, model)
```

Creates an executor based on the model type.

**Arguments**:

- `global_time` _float_ - Global simulation time
- `ins_t` _float_ - Instance creation time
- `des_t` _float_ - Destruction time
- `en_name` _str_ - Engine name
  model(ModelType.BEHAVIORAL of ModelType.STRUCTURAL): The model to execute
  

**Returns**:

- `Executor` - The created executor

<a id="pyjevsim.executor_factory.ExecutorFactory.create_behavior_executor"></a>

#### create\_behavior\_executor

```python
def create_behavior_executor(_, ins_t, des_t, en_name, model)
```

Create BehaviorModelexecutor

**Arguments**:

- `_` _float_ - Unused global time
- `ins_t` _float_ - Instance creation time
- `des_t` _float_ - Destruction time
- `en_name` _str_ - SysExecutor name / 엔진 이름
- `model` _BehaviorModel_ - Behavior model to execute / 실행할 동작 모델
  

**Returns**:

- `BehaviorModelExecutor` - The created BehaviorModelexecutor

<a id="pyjevsim.executor_factory.ExecutorFactory.create_structural_executor"></a>

#### create\_structural\_executor

```python
def create_structural_executor(global_time, ins_t, des_t, en_name, model)
```

Create StructuralModelExecutor

**Arguments**:

- `global_time` _float_ - Global simulation time
- `ins_t` _float_ - Instance creation time
- `des_t` _float_ - Destruction time
- `en_name` _str_ - SysExecutor name
- `model` _StructuralModel_ - StructuralModel to execute
  

**Returns**:

- `StructuralModelExecutor` - created StructuralModelExecutor

<a id="pyjevsim.executor_factory.ExecutorFactory.create_snapshot_behavior_executor"></a>

#### create\_snapshot\_behavior\_executor

```python
def create_snapshot_behavior_executor(_, ins_t, des_t, en_name, model,
                                      snapshot_condition)
```

Create SnapshotExecutor.
The SnapshotExecutor decorates a BehaviorModelExecutor to store data from a running BehaviorModel under certain conditions.

**Arguments**:

- `_` _float_ - Unused global time
- `ins_t` _float_ - Instance creation time
- `des_t` _float_ - Destruction time
- `en_name` _str_ - SysExecutor name
- `model` _BehaviorModel_ - The behavior model to execute
- `snapshot_condition` _Callable_ - The condition to take snapshots
  

**Returns**:

- `SnapshotExecutor` - The created SnapshotExecutor

<a id="pyjevsim.executor_snapshot_manager"></a>

# pyjevsim.executor\_snapshot\_manager

<a id="pyjevsim.executor_snapshot_manager.ExecutorSnapshotManager"></a>

## ExecutorSnapshotManager Objects

```python
class ExecutorSnapshotManager()
```

Manager class for taking and loading snapshots of SysExecutor.

<a id="pyjevsim.executor_snapshot_manager.ExecutorSnapshotManager.snapshot_executor"></a>

#### snapshot\_executor

```python
def snapshot_executor(engine)
```

Take snapshot of Sysexecutor.

**Arguments**:

- `engine(SysExecutor)` - SysExecutor to snapshot
  

**Returns**:

- `bytes` - Serialized snapshot of the Sysexecutor

<a id="pyjevsim.executor_snapshot_manager.ExecutorSnapshotManager.load_snapshot"></a>

#### load\_snapshot

```python
def load_snapshot(shotengine)
```

Loads Sysexecutor snapshot.

**Arguments**:

- `shotengine` _bytes_ - Serialized snapshot of the engine
  

**Returns**:

- `object(SysExecutor)` - loaded SysExecutor

<a id="pyjevsim.executor_snapshot_manager.ExecutorSnapshotManager.cleansing"></a>

#### cleansing

```python
def cleansing(model)
```

Returns model that does not use a SnapshotExecutor as a BehaviorExecutor Type.

**Arguments**:

- `model(SnapshotExecutor)` - SnapshotExecutor to cleanse
  

**Returns**:

- `object` - BehaviorExecutor

<a id="pyjevsim.model_snapshot_manager"></a>

# pyjevsim.model\_snapshot\_manager

<a id="pyjevsim.model_snapshot_manager.ModelSnapshotManager"></a>

## ModelSnapshotManager Objects

```python
class ModelSnapshotManager()
```

Manager class for handling model snapshots.

<a id="pyjevsim.model_snapshot_manager.ModelSnapshotManager.snapshot_simulation"></a>

#### snapshot\_simulation

```python
def snapshot_simulation(relation_map, model_map, name, directory_path=".")
```

Takes a snapshot of the simulation.
Snapshot simulation model information and relationships to the “directory_path/name” location.

**Arguments**:

- `relation_map` _dict_ - The relation map of SysExecutor
- `model_map` _dict_ - The model map of SysExecutor
- `name` _str_ - The name of Simulation
- `directory_path` _str_ - The directory path to save the snapshot

<a id="pyjevsim.model_snapshot_manager.ModelSnapshotManager.register_snapshot_executor"></a>

#### register\_snapshot\_executor

```python
def register_snapshot_executor(name, snapshot_executor_generator)
```

Register SnapshotExecutor.

**Arguments**:

- `name` _str_ - name of SnapshotExecutor
  snapshot_executor_generator : The generator function for SnapshotExecutor

<a id="pyjevsim.model_snapshot_manager.ModelSnapshotManager.check_snapshot_executor"></a>

#### check\_snapshot\_executor

```python
def check_snapshot_executor(name)
```

Checks if a snapshot executor exists.

**Arguments**:

- `name` _str_ - The name of SnapshotExecutor
  

**Returns**:

- `bool` - True if exists, False otherwise

<a id="pyjevsim.model_snapshot_manager.ModelSnapshotManager.create_snapshot_executor"></a>

#### create\_snapshot\_executor

```python
def create_snapshot_executor(behavior_executor)
```

Create SnapshotExecutor.

**Arguments**:

- `behavior_executor` _BehaviorModelExecutor_ - BehaviorModelExecutor
  

**Returns**:

- `object` - created SnapshotExecutor / 생성된 스냅샷 실행기

<a id="pyjevsim.model_snapshot_manager.ModelSnapshotManager.load_snapshot"></a>

#### load\_snapshot

```python
def load_snapshot(name, shotmodel)
```

Loads BehaviorModel.

**Arguments**:

- `name` _str_ - The name of Model
- `shotmodel` _bytes_ - Binary data of the model snapshot
  

**Returns**:

- `object(BehaivorModel)` - The loaded model
  

**Raises**:

- `Exception` - If the model type is not ModelType.BEHAVIORAL

<a id="pyjevsim.snapshot_executor"></a>

# pyjevsim.snapshot\_executor

<a id="pyjevsim.snapshot_executor.SnapshotExecutor"></a>

## SnapshotExecutor Objects

```python
class SnapshotExecutor(Executor)
```

Framework for adding snapshot conditions to behavior models.
It is a decorated form of BehaviorExecutor, 
inheriting from that class and entering snapshot conditions. 
The snapshot condition can be before or after a function in the behavior model.

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.create_executor"></a>

#### create\_executor

```python
@abstractstaticmethod
def create_executor(cls, behavior_executor)
```

Creates a SnapshotExecutor instance.

**Arguments**:

- `cls` _type_ - Name of created class
  behavior_executor (BehaviorExecutor):BehaviorExecutor to decorate

**Returns**:

- `SnapshotExecutor` - The created snapshot executor

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.__init__"></a>

#### \_\_init\_\_

```python
def __init__(behavior_executor)
```

**Arguments**:

- `behavior_executor` _BehaviorExecutor_ - BehaviorExecutor to decorate

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.get_core_model"></a>

#### get\_core\_model

```python
def get_core_model()
```

Returns BehaviorModel of SnapshotExecutor.

**Returns**:

- `CoreModel` - BehaviorModel

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.__str__"></a>

#### \_\_str\_\_

```python
def __str__()
```

Returns the string representation of SnapshotExecutor.

**Returns**:

- `str` - String representation

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.get_name"></a>

#### get\_name

```python
def get_name()
```

Returns the name of SnapshotExecutor.

**Returns**:

- `str` - Name

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.get_engine_name"></a>

#### get\_engine\_name

```python
def get_engine_name()
```

Returns SysExecutor name of SnapshotExecutor.

**Returns**:

- `str` - SysExecutor name

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.set_engine_name"></a>

#### set\_engine\_name

```python
def set_engine_name(engine_name)
```

Sets SysExecutor name of SnapshotExecutor.

**Arguments**:

- `engine_name` _str_ - SysExecutor name

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.get_create_time"></a>

#### get\_create\_time

```python
def get_create_time()
```

Returns the creation time of SnapshotExecutor.

**Returns**:

- `float` - Creation time

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.get_destruct_time"></a>

#### get\_destruct\_time

```python
def get_destruct_time()
```

Returns the destruction time of SnapshotExecutor.

**Returns**:

- `float` - Destruction time

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.get_obj_id"></a>

#### get\_obj\_id

```python
def get_obj_id()
```

Return object ID of SnapshotExecutor.

**Returns**:

- `int` - Object ID

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.get_cur_state"></a>

#### get\_cur\_state

```python
def get_cur_state()
```

Returns the current state of SnapshotExecutor.

**Returns**:

- `str` - Current state

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.init_state"></a>

#### init\_state

```python
def init_state(state)
```

Initializes the state of SnapshotExecutor.

**Arguments**:

- `state` _str_ - The state to set / 설정할 상태

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.ext_trans"></a>

#### ext\_trans

```python
def ext_trans(port, msg)
```

Handles the external transition.

**Arguments**:

- `port` _str_ - The port name
- `msg` _Message_ - The message

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.int_trans"></a>

#### int\_trans

```python
def int_trans()
```

Handles the internal transition.

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.output"></a>

#### output

```python
def output()
```

Handles the output function.

**Returns**:

- `Message` - The output message

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.time_advance"></a>

#### time\_advance

```python
def time_advance()
```

Returns the time advance value.

**Returns**:

- `float` - Time advance value

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.set_req_time"></a>

#### set\_req\_time

```python
def set_req_time(global_time)
```

Sets the request time.

**Arguments**:

- `global_time` _float_ - Simulation time

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.get_req_time"></a>

#### get\_req\_time

```python
def get_req_time()
```

Returns the request time.

**Returns**:

- `float` - Request time

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.snapshot_time_condition"></a>

#### snapshot\_time\_condition

```python
@abstractmethod
def snapshot_time_condition(global_time)
```

Abstract method for snapshot time condition.

**Arguments**:

- `global_time` _float_ - The global time / simulation time

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.snapshot_pre_condition_ext"></a>

#### snapshot\_pre\_condition\_ext

```python
@abstractmethod
def snapshot_pre_condition_ext(port, msg, cur_state)
```

Abstract method for pre-condition of external transition snapshot.

**Arguments**:

- `port` _str_ - The port name
- `msg` _SysMessage_ - The message
- `cur_state` _str_ - The current state

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.snapshot_post_condition_ext"></a>

#### snapshot\_post\_condition\_ext

```python
@abstractmethod
def snapshot_post_condition_ext(port, msg, cur_state)
```

Abstract method for post-condition of external transition snapshot.

**Arguments**:

- `port` _str_ - The port name
- `msg` _SysMessage_ - The message
- `cur_state` _str_ - The current state

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.snapshot_pre_condition_int"></a>

#### snapshot\_pre\_condition\_int

```python
@abstractmethod
def snapshot_pre_condition_int(cur_state)
```

Abstract method for pre-condition of internal transition snapshot.

**Arguments**:

- `cur_state` _str_ - The current state

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.snapshot_post_condition_int"></a>

#### snapshot\_post\_condition\_int

```python
@abstractmethod
def snapshot_post_condition_int(cur_state)
```

Abstract method for post-condition of internal transition snapshot.

**Arguments**:

- `cur_state` _str_ - The current state

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.snapshot_pre_condition_out"></a>

#### snapshot\_pre\_condition\_out

```python
@abstractmethod
def snapshot_pre_condition_out(cur_state)
```

Abstract method for pre-condition of output snapshot.

**Arguments**:

- `cur_state` _str_ - The current state

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.snapshot_post_condition_out"></a>

#### snapshot\_post\_condition\_out

```python
@abstractmethod
def snapshot_post_condition_out(msg, cur_state)
```

Abstract method for post-condition of output snapshot.

**Arguments**:

- `msg` _SysMessage_ - The message
- `cur_state` _str_ - The current state

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.snapshot"></a>

#### snapshot

```python
@abstractmethod
def snapshot(name)
```

An abstract method that creates a method to take a snapshot.
You can use the snapshot method in a conditional method.
Use the model_dump method to get the model data in bytes.
Save that data to the DB or save it to a file.

**Arguments**:

- `name` _str_ - The name of the snapshot

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.model_dump"></a>

#### model\_dump

```python
def model_dump()
```

Dumps BehaviorModel

**Returns**:

- `bytes` - The dumped BehaviorModel

<a id="pyjevsim.snapshot_executor.SnapshotExecutor.get_behavior_executor"></a>

#### get\_behavior\_executor

```python
def get_behavior_executor()
```

Return BehaviorExecutor.

**Returns**:

- `BehaviorExecutor` - The behavior executor / 동작 실행기

<a id="pyjevsim.snapshot_manager"></a>

# pyjevsim.snapshot\_manager

<a id="pyjevsim.snapshot_manager.SnapshotManager"></a>

## SnapshotManager Objects

```python
class SnapshotManager()
```

The ModelSnapshotManager reads the snapshotted simulation(the directory where all the models and their releases are stored)
and returns it as a SysExecutor.

<a id="pyjevsim.snapshot_manager.SnapshotManager.__init__"></a>

#### \_\_init\_\_

```python
def __init__(t_resol, ex_mode, name, path=".")
```

Initializes the SnapshotManager with time resolution, execution mode, name, and path.

**Arguments**:

- `t_resol` _float_ - Time resolution
- `ex_mode` _R_TIME or V_TIME_ - Execution mode(Real time or Virtual time)
- `name` _str_ - Name of SysExecutor
- `path` _str, optional_ - Path to load snapshots

<a id="pyjevsim.snapshot_manager.SnapshotManager.set_engine"></a>

#### set\_engine

```python
def set_engine()
```

Sets up SysExecutor with the relation map and model map.

<a id="pyjevsim.snapshot_manager.SnapshotManager.load_models"></a>

#### load\_models

```python
def load_models(model_list)
```

Loads models from files and registers them with SysExecutor.

**Arguments**:

- `model_list` _list_ - List of model names

<a id="pyjevsim.snapshot_manager.SnapshotManager.relations"></a>

#### relations

```python
def relations(relation_map)
```

Sets up coupling relations in SysExecutor.

**Arguments**:

- `relation_map` _dict_ - The relation map / 관계 맵

<a id="pyjevsim.snapshot_manager.SnapshotManager.get_engine"></a>

#### get\_engine

```python
def get_engine()
```

Returns the SysExecutor.

**Returns**:

  Restored SysExecutor

<a id="pyjevsim.structural_executor"></a>

# pyjevsim.structural\_executor

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.structural_executor_model"></a>

# pyjevsim.structural\_executor\_model

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.structural_model"></a>

# pyjevsim.structural\_model

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.system_executor"></a>

# pyjevsim.system\_executor

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.system_executor.SysExecutor"></a>

## SysExecutor Objects

```python
class SysExecutor(CoreModel)
```

SysExecutor managing the execution of models in a simulation.(Simulation Engine)

<a id="pyjevsim.system_executor.SysExecutor.__init__"></a>

#### \_\_init\_\_

```python
def __init__(_time_resolution,
             _sim_name="default",
             ex_mode=ExecutionType.V_TIME,
             snapshot_manager=None)
```

Initializes the SysExecutor with time resolution, simulation name, execution mode, and optional snapshot manager.

**Arguments**:

- `_time_resolution` _float_ - The time resolution for the simulation
- `_sim_name` _str, optional_ - The name of the simulation
- `ex_mode` _R_TIME or VTIME_ - The execution mode
- `snapshot_manager` _ModelSnapshotManager, optional_ - Manages SnapshotExecutor

<a id="pyjevsim.system_executor.SysExecutor.get_global_time"></a>

#### get\_global\_time

```python
def get_global_time()
```

Retrieves the current global time.(simulation time)

**Returns**:

- `float` - The current global time

<a id="pyjevsim.system_executor.SysExecutor.set_snapshot_manager"></a>

#### set\_snapshot\_manager

```python
def set_snapshot_manager(snapshot_manager)
```

Sets the snapshot manager.

**Arguments**:

- `snapshot_manager` _ModelSnapshotManager_ - The snapshot manager to set

<a id="pyjevsim.system_executor.SysExecutor.register_entity"></a>

#### register\_entity

```python
def register_entity(entity, inst_t=0, dest_t=Infinite, ename="default")
```

Register simulation entity(Model).

**Arguments**:

- `entity` _BehaviorModel or StructuralModel_ - The entity to register
- `inst_t` _float, optional_ - Instance creation time
- `dest_t` _float, optional_ - Destruction time
- `ename` _str, optional_ - SysExecutor name

<a id="pyjevsim.system_executor.SysExecutor.get_entity"></a>

#### get\_entity

```python
def get_entity(model_name)
```

Retrieves entities by model name.

**Arguments**:

- `model_name` _str_ - The name of the model
  

**Returns**:

- `list` - List of entities

<a id="pyjevsim.system_executor.SysExecutor.get_model"></a>

#### get\_model

```python
def get_model(name)
```

Retrieve Model by name.

**Arguments**:

- `name` _str_ - The name of the model
  

**Returns**:

- `CoreModel` - Model(BehaviorModel or StructuralModel)

<a id="pyjevsim.system_executor.SysExecutor.remove_entity"></a>

#### remove\_entity

```python
def remove_entity(model_name)
```

Removes an entity by model name.

**Arguments**:

- `model_name` _str_ - The name of the model

<a id="pyjevsim.system_executor.SysExecutor.create_entity"></a>

#### create\_entity

```python
def create_entity()
```

Creates entities that are scheduled for creation.

<a id="pyjevsim.system_executor.SysExecutor.destory_entity"></a>

#### destory\_entity

```python
def destory_entity(delete_lst)
```

Destroys a list of entities.

**Arguments**:

- `delete_lst` _list_ - List of entities to delete

<a id="pyjevsim.system_executor.SysExecutor.destroy_active_entity"></a>

#### destroy\_active\_entity

```python
def destroy_active_entity()
```

Destroys active entities that are scheduled for destruction.

<a id="pyjevsim.system_executor.SysExecutor.coupling_relation"></a>

#### coupling\_relation

```python
def coupling_relation(src_obj, out_port, dst_obj, in_port)
```

Related Model's input/output ports to each other.
Related src_obj's output port to dst_obj's input port.

**Arguments**:

- `src_obj` _BehaviorMdoel or StructuralModel_ - Model to relate as output ports
- `out_port` _str_ - src_obj's output port
- `dst_obj` _CoreModel_ - Model to relate as input ports
- `in_port` _str_ - dst_obj's input port

<a id="pyjevsim.system_executor.SysExecutor.get_relation"></a>

#### get\_relation

```python
def get_relation()
```

Retrieves the current coupling relations.

**Returns**:

- `dict` - The relation map

<a id="pyjevsim.system_executor.SysExecutor.remove_relation"></a>

#### remove\_relation

```python
def remove_relation(src, out_port, dst, in_port)
```

Removes a coupling relation.

**Arguments**:

- `src_obj` _BehaviorMdoel or StructuralModel_ - Models that remove relationships as output port
- `out_port` _str_ - src_obj's output port
- `dst_obj` _CoreModel_ - Models that remove relationships as input port
- `in_port` _str_ - dst_obj's input port

<a id="pyjevsim.system_executor.SysExecutor.reset_relation"></a>

#### reset\_relation

```python
def reset_relation()
```

Resets all coupling relations.

<a id="pyjevsim.system_executor.SysExecutor.single_output_handling"></a>

#### single\_output\_handling

```python
def single_output_handling(obj, msg)
```

Handles a single output message.

**Arguments**:

- `obj` _BehaviorModel or StructuralModel_ - Model
- `msg` _SysMessage_ - The message

<a id="pyjevsim.system_executor.SysExecutor.output_handling"></a>

#### output\_handling

```python
def output_handling(obj, msg)
```

Handles output messages.

**Arguments**:

- `obj` _BehaviorModel or StructuralModel_ - Model
- `msg` _SysMessage_ - The message

<a id="pyjevsim.system_executor.SysExecutor.init_sim"></a>

#### init\_sim

```python
def init_sim()
```

Initializes the simulation.

<a id="pyjevsim.system_executor.SysExecutor.schedule"></a>

#### schedule

```python
def schedule()
```

Schedules the next simulation event.

<a id="pyjevsim.system_executor.SysExecutor.simulate"></a>

#### simulate

```python
def simulate(_time=Infinite, _tm=True)
```

Runs the simulation for a given amount of time.

**Arguments**:

- `_time` _float_ - The simulation time
- `_tm` _bool_ - Whether to use the termination manager

<a id="pyjevsim.system_executor.SysExecutor.simulation_stop"></a>

#### simulation\_stop

```python
def simulation_stop()
```

Stops the simulation and resets SysExecutor.

<a id="pyjevsim.system_executor.SysExecutor.insert_external_event"></a>

#### insert\_external\_event

```python
def insert_external_event(_port, _msg, scheduled_time=0)
```

Inserts an external event into the simulation.

**Arguments**:

- `_port` _str_ - port name
- `_msg` _SysMessage or None_ - Event message
- `scheduled_time` _float, optional_ - The scheduled time for the event

<a id="pyjevsim.system_executor.SysExecutor.insert_custom_external_event"></a>

#### insert\_custom\_external\_event

```python
def insert_custom_external_event(_port, _bodylist, scheduled_time=0)
```

Inserts a custom external event into the simulation.

**Arguments**:

- `_port` _str_ - The port name / 포트 이름
- `_bodylist` _list_ - The list of message bodies
- `scheduled_time` _float, optional_ - The scheduled time for the event

<a id="pyjevsim.system_executor.SysExecutor.get_generated_event"></a>

#### get\_generated\_event

```python
def get_generated_event()
```

Returns the queue of generated events.

**Returns**:

- `deque` - The queue of generated events

<a id="pyjevsim.system_executor.SysExecutor.handle_external_input_event"></a>

#### handle\_external\_input\_event

```python
def handle_external_input_event()
```

Handles external input events.

<a id="pyjevsim.system_executor.SysExecutor.handle_external_output_event"></a>

#### handle\_external\_output\_event

```python
def handle_external_output_event()
```

Handles external output events and clears the output event queue.

**Returns**:

- `list` - List of output events

<a id="pyjevsim.system_executor.SysExecutor.is_terminated"></a>

#### is\_terminated

```python
def is_terminated()
```

Checks if the simulation is terminated.

**Returns**:

- `bool` - True if terminated, False otherwise

<a id="pyjevsim.system_executor.SysExecutor.snapshot_simulation"></a>

#### snapshot\_simulation

```python
def snapshot_simulation(name="", directory_path=".")
```

Snapshot the model and its releases.

Args :
name(str) : Name of the simulation to be snapshot
directory_path : Where the simulation will be snapshot

**Raises**:

- `ValueError` - Snapshot manager is not set.

<a id="pyjevsim.system_message"></a>

# pyjevsim.system\_message

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.system_message.SysMessage"></a>

## SysMessage Objects

```python
class SysMessage(SystemObject)
```

SysMessage for handling messages(port and data) between Models.

<a id="pyjevsim.system_message.SysMessage.__init__"></a>

#### \_\_init\_\_

```python
def __init__(src_name="", dst_name="")
```

**Arguments**:

- `src_name` _str_ - The source name(Model name)
- `dst_name` _str_ - The destination name(port)

<a id="pyjevsim.system_message.SysMessage.__str__"></a>

#### \_\_str\_\_

```python
def __str__()
```

Returns the string representation of the message.

**Returns**:

- `str` - The string representation

<a id="pyjevsim.system_message.SysMessage.insert"></a>

#### insert

```python
def insert(msg)
```

Inserts a message into the message list(data).

**Arguments**:

- `msg` _any_ - The message to insert

<a id="pyjevsim.system_message.SysMessage.extend"></a>

#### extend

```python
def extend(_list)
```

Extends the message list with multiple messages.

**Arguments**:

- `_list` _list_ - The list of messages to add

<a id="pyjevsim.system_message.SysMessage.retrieve"></a>

#### retrieve

```python
def retrieve()
```

Retrieves the list of messages.

**Returns**:

- `list` - The list of messages

<a id="pyjevsim.system_message.SysMessage.get_src"></a>

#### get\_src

```python
def get_src()
```

Returns the source(model) name of the message.

**Returns**:

- `str` - The source name

<a id="pyjevsim.system_message.SysMessage.get_dst"></a>

#### get\_dst

```python
def get_dst()
```

Returns the destination(port) name of the message.

**Returns**:

- `str` - The destination(port) name

<a id="pyjevsim.system_message.SysMessage.set_msg_time"></a>

#### set\_msg\_time

```python
def set_msg_time(_time)
```

Sets the message time.

**Arguments**:

- `_time` _float_ - The time to set

<a id="pyjevsim.system_message.SysMessage.get_msg_time"></a>

#### get\_msg\_time

```python
def get_msg_time()
```

Returns the message time.

**Returns**:

- `float` - The message time

<a id="pyjevsim.system_object"></a>

# pyjevsim.system\_object

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.system_object.SystemObject"></a>

## SystemObject Objects

```python
class SystemObject()
```

Base class for all system objects, providing unique object IDs and creation time.

<a id="pyjevsim.system_object.SystemObject.__str__"></a>

#### \_\_str\_\_

```python
def __str__()
```

Returns the string representation of the SystemObject.

**Returns**:

- `str` - The string representation

<a id="pyjevsim.system_object.SystemObject.__lt__"></a>

#### \_\_lt\_\_

```python
def __lt__(other)
```

Compares this object with another object for sorting.

**Arguments**:

- `other` _SystemObject_ - The other object to compare with
  

**Returns**:

- `bool` - True if this object ID is less than the other object's ID

<a id="pyjevsim.system_object.SystemObject.get_obj_id"></a>

#### get\_obj\_id

```python
def get_obj_id()
```

Returns the unique object ID.

**Returns**:

- `int` - The unique object ID

<a id="pyjevsim.termination_manager"></a>

# pyjevsim.termination\_manager

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="test_banksim"></a>

# test\_banksim

<a id="test_banksim.banksim_classic"></a>

# test\_banksim.banksim\_classic

<a id="test_banksim.banksim_model_restore"></a>

# test\_banksim.banksim\_model\_restore

<a id="test_banksim.banksim_model_snapshot"></a>

# test\_banksim.banksim\_model\_snapshot

<a id="test_banksim.banksim_restore"></a>

# test\_banksim.banksim\_restore

<a id="test_banksim.banksim_snapshot"></a>

# test\_banksim.banksim\_snapshot

<a id="test_banksim.model_acoountant"></a>

# test\_banksim.model\_acoountant

<a id="test_banksim.model_acoountant.BankAccountant"></a>

## BankAccountant Objects

```python
class BankAccountant(BehaviorModel)
```

A Model representing a bank accountant processing bank users.

<a id="test_banksim.model_acoountant.BankAccountant.__init__"></a>

#### \_\_init\_\_

```python
def __init__(name, proc_num)
```

Initializes the BankAccountant with states and ports.

**Arguments**:

- `name` _str_ - Name of the accountant
- `proc_num` _int_ - Processor number for identification

<a id="test_banksim.model_acoountant.BankAccountant.ext_trans"></a>

#### ext\_trans

```python
def ext_trans(port, msg)
```

Handles external transitions based on the input port.

**Arguments**:

- `port` _str_ - The port that received the message
- `msg` _SysMessage_ - The received message

<a id="test_banksim.model_acoountant.BankAccountant.output"></a>

#### output

```python
def output()
```

Generates the output message when in the "PROC" state.

**Returns**:

- `SysMessage` - The output message

<a id="test_banksim.model_acoountant.BankAccountant.int_trans"></a>

#### int\_trans

```python
def int_trans()
```

Handles internal transitions based on the current state.

<a id="test_banksim.model_acoountant.BankAccountant.__del__"></a>

#### \_\_del\_\_

```python
def __del__()
```

Destructor to print the log of processed users.

<a id="test_banksim.model_acoountant.BankAccountant.__str__"></a>

#### \_\_str\_\_

```python
def __str__()
```

Returns a string representation of the BankAccountant.

**Returns**:

- `str` - String representation

<a id="test_banksim.model_queue"></a>

# test\_banksim.model\_queue

<a id="test_banksim.model_queue.BankQueue"></a>

## BankQueue Objects

```python
class BankQueue(BehaviorModel)
```

Class representing a bank queue managing users and processors.

<a id="test_banksim.model_queue.BankQueue.__init__"></a>

#### \_\_init\_\_

```python
def __init__(name, queue_size, proc_num)
```

**Arguments**:

- `name` _str_ - Name of Model
- `queue_size` _int_ - Maximum size of the queue
- `proc_num` _int_ - Number of processors

<a id="test_banksim.model_queue.BankQueue.set_queue_size"></a>

#### set\_queue\_size

```python
def set_queue_size(queue_size)
```

Sets the maximum size of the queue.

**Arguments**:

- `queue_size` _int_ - Maximum size of the queue

<a id="test_banksim.model_queue.BankQueue.ext_trans"></a>

#### ext\_trans

```python
def ext_trans(port, msg)
```

Handles external transitions based on the input port.

**Arguments**:

- `port` _str_ - The port that received the message
- `msg` _SysMessage_ - The received message

<a id="test_banksim.model_queue.BankQueue.output"></a>

#### output

```python
def output()
```

Generates the output message when in the "SEND" state.

**Returns**:

- `SysMessage` - The output message

<a id="test_banksim.model_queue.BankQueue.int_trans"></a>

#### int\_trans

```python
def int_trans()
```

Handles internal transitions based on the current state.

<a id="test_banksim.model_queue.BankQueue.set_proc_num"></a>

#### set\_proc\_num

```python
def set_proc_num(proc_num)
```

Sets the number of processors and adjusts the usable processor list.

**Arguments**:

- `proc_num` _int_ - Number of processors

<a id="test_banksim.model_queue.BankQueue.__str__"></a>

#### \_\_str\_\_

```python
def __str__()
```

Returns a string representation of the BankQueue.

**Returns**:

- `str` - String representation

<a id="test_banksim.model_user_gen"></a>

# test\_banksim.model\_user\_gen

<a id="test_banksim.model_user_gen.BankUser"></a>

## BankUser Objects

```python
class BankUser()
```

<a id="test_banksim.model_user_gen.BankUser.__init__"></a>

#### \_\_init\_\_

```python
def __init__(_id: int, s_t: float)
```

**Arguments**:

- `_id` _int_ - User ID
- `s_t` _float_ - Service time

<a id="test_banksim.model_user_gen.BankUser.get_id"></a>

#### get\_id

```python
def get_id() -> int
```

**Returns**:

- `int` - User ID

<a id="test_banksim.model_user_gen.BankUser.get_wait_time"></a>

#### get\_wait\_time

```python
def get_wait_time() -> float
```

**Returns**:

- `float` - Wait time

<a id="test_banksim.model_user_gen.BankUser.get_arrival_time"></a>

#### get\_arrival\_time

```python
def get_arrival_time() -> float
```

**Returns**:

- `float` - Arrival time

<a id="test_banksim.model_user_gen.BankUser.get_service_time"></a>

#### get\_service\_time

```python
def get_service_time() -> float
```

**Returns**:

- `float` - Service time

<a id="test_banksim.model_user_gen.BankUser.set_arrival_time"></a>

#### set\_arrival\_time

```python
def set_arrival_time(a_t: float) -> None
```

**Arguments**:

- `a_t` _float_ - Arrival time

<a id="test_banksim.model_user_gen.BankUser.calc_wait_time"></a>

#### calc\_wait\_time

```python
def calc_wait_time(w_t: float) -> None
```

Calculates the wait time.

**Arguments**:

- `w_t` _float_ - Done time

<a id="test_banksim.model_user_gen.BankUser.__str__"></a>

#### \_\_str\_\_

```python
def __str__()
```

Returns a string representation of the BankUser.

**Returns**:

- `str` - String representation

<a id="test_banksim.model_user_gen.BankUserGenerator"></a>

## BankUserGenerator Objects

```python
class BankUserGenerator(BehaviorModel)
```

A Model representing a bank user generator.

<a id="test_banksim.model_user_gen.BankUserGenerator.__init__"></a>

#### \_\_init\_\_

```python
def __init__(name, cycle, max_user, proc_time)
```

**Arguments**:

- `name` _str_ - Name of Model
- `cycle` _float_ - Generation cycle time
- `max_user` _int_ - Maximum number of users to generate
- `proc_time` _float_ - Processing time for each user

<a id="test_banksim.model_user_gen.BankUserGenerator.ext_trans"></a>

#### ext\_trans

```python
def ext_trans(port, msg)
```

Handles external transitions based on the input port.

**Arguments**:

- `port` _str_ - The port that received the message
- `msg` _SysMessage_ - The received message

<a id="test_banksim.model_user_gen.BankUserGenerator.output"></a>

#### output

```python
def output()
```

Generates the output message when in the "GEN" state.

**Returns**:

- `SysMessage` - The output message

<a id="test_banksim.model_user_gen.BankUserGenerator.int_trans"></a>

#### int\_trans

```python
def int_trans()
```

Handles internal transitions based on the current state.

<a id="test_banksim.model_user_gen.BankUserGenerator.set_cycle"></a>

#### set\_cycle

```python
def set_cycle(cycle)
```

Sets the generation cycle time.

**Arguments**:

- `cycle` _float_ - Generation cycle time

