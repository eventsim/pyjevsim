<a id="pyjevsim"></a>

# pyjevsim

Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2014-2020 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

<a id="pyjevsim.behavior_model"></a>

# pyjevsim.behavior\_model

<a id="pyjevsim.behavior_model.BehaviorModel"></a>

## BehaviorModel

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

<a id="pyjevsim.executor_snapshot_manager"></a>

# pyjevsim.executor\_snapshot\_manager

<a id="pyjevsim.executor_snapshot_manager.ExecutorSnapshotManager"></a>

## ExecutorSnapshotManager

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

## ModelSnapshotManager

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

## SnapshotExecutor

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

<a id="pyjevsim.snapshot_manager"></a>

# pyjevsim.snapshot\_manager

<a id="pyjevsim.snapshot_manager.SnapshotManager"></a>

## SnapshotManager

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

<a id="pyjevsim.snapshot_manager.SnapshotManager.load_models"></a>

#### load\_models

```python
def load_models(model_list)
```

Loads models from files and registers them with SysExecutor.

**Arguments**:

- `model_list` _list_ - List of model names

<a id="pyjevsim.snapshot_manager.SnapshotManager.get_engine"></a>

#### get\_engine

```python
def get_engine()
```

Returns the SysExecutor.

**Returns**:

  Restored SysExecutor

<a id="pyjevsim.system_executor"></a>

# pyjevsim.system\_executor

<a id="pyjevsim.system_executor.SysExecutor"></a>

## SysExecutor
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

<a id="pyjevsim.system_executor.SysExecutor.remove_entity"></a>

#### remove\_entity

```python
def remove_entity(model_name)
```

Removes an entity by model name.

**Arguments**:

- `model_name` _str_ - The name of the model

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

<a id="pyjevsim.system_message"></a>

# pyjevsim.system\_message

<a id="pyjevsim.system_message.SysMessage"></a>

## SysMessage 

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