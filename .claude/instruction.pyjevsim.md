# pyjevsim Development Instructions

## Project Overview
pyjevsim is a DEVS (Discrete Event System Specification) simulation framework with journaling (snapshot/restore) capabilities. The framework follows strict DEVS formalism for discrete event simulation.

## Core Architecture Principles

### 1. DEVS Formalism Compliance
- **MUST** follow DEVS execution semantics: `output() → int_trans() → reschedule`
- **MUST** maintain separation between atomic models (BehaviorModel) and coupled models (StructuralModel)
- **NEVER** violate the strict time advancement and event ordering rules

### 2. Model Types
#### BehaviorModel (Atomic Models)
- State-based execution with configurable deadlines
- **MUST** implement three abstract methods:
  - `ext_trans(port, msg)`: External transition function
  - `int_trans()`: Internal transition function
  - `output(msg_deliver)`: Output function
- States stored in `_states` dict with deadline values
- Current state tracked in `_cur_state`

#### StructuralModel (Coupled Models)
- Container for sub-models
- Manages internal coupling via `port_map`
- **NO** state transitions (delegated to sub-models)

### 3. Executor Pattern
- Models are wrapped by executors (BehaviorExecutor, StructuralExecutor)
- ExecutorFactory creates appropriate executor types
- **ALWAYS** use factory pattern for executor creation
- Executors manage timing, transitions, and message delivery

### 4. Simulation Engine (SysExecutor)
- Manages global time, event scheduling, and model lifecycle
- Uses priority queue (ScheduleQueue) for event scheduling
- Supports both virtual time (V_TIME) and real-time (R_TIME) execution
- **NEVER** manipulate `global_time` directly outside of `schedule()` loop

## Development Guidelines

### Code Quality Standards
1. **Type Hints**: Use Python type hints for all function parameters and return values
2. **Docstrings**: Follow Google-style docstrings with Args/Returns/Raises sections
3. **Error Handling**: Validate inputs and raise meaningful exceptions
4. **Thread Safety**: Use locks when modifying shared state (e.g., `input_event_queue`)

### Naming Conventions
- **Variables**: Snake_case (e.g., `global_time`, `active_obj_map`)
- **Methods**: Snake_case (e.g., `ext_trans`, `coupling_relation`)
- **Classes**: PascalCase (e.g., `BehaviorModel`, `SysExecutor`)
- **Constants**: UPPER_CASE (e.g., `EXTERNAL_SRC`, `EXTERNAL_DST`)
- **Private attributes**: Prefix with `_` (e.g., `_cur_state`, `_states`)

### File Organization
```
pyjevsim/
├── core_model.py           # Base model class
├── behavior_model.py       # Atomic model template
├── structural_model.py     # Coupled model template
├── system_executor.py      # Simulation engine
├── executor.py             # Executor implementations
├── executor_factory.py     # Factory pattern
├── schedule_queue.py       # Priority queue
├── system_message.py       # Message objects
├── snapshot_*.py           # Snapshot/restore system
└── definition.py           # Enums and constants
```

### Testing Requirements
- **MUST** write pytest tests for new features
- Test files in `tests/` directory
- Cover both behavioral and structural model scenarios
- Test snapshot/restore functionality if applicable
- Run tests with: `pytest tests/`

### Example Structure
- Place examples in `examples/<feature_name>/`
- Include basic, snapshot, and restore variants
- Follow naming: `<feature>.py`, `<feature>_snapshot.py`, `<feature>_restore.py`

## Feature Development Workflow

### 1. Planning Phase
```
1. Identify if feature is:
   - Core engine enhancement (system_executor.py)
   - Model capability (behavior_model.py, structural_model.py)
   - Utility/helper (new module)
   - Snapshot/restore related (snapshot_*.py)

2. Check DEVS formalism compliance
3. Design API to match existing patterns
```

### 2. Implementation Phase
```python
# Example: Adding new model feature
class BehaviorModel(CoreModel):
    def new_feature(self, param: type) -> return_type:
        """
        Brief description.

        Args:
            param (type): Description

        Returns:
            return_type: Description

        Raises:
            ValueError: When condition
        """
        # Implementation
        pass
```

### 3. Testing Phase
```python
# tests/test_new_feature.py
import pytest
from pyjevsim import BehaviorModel, SysExecutor

class TestModel(BehaviorModel):
    def __init__(self, name):
        super().__init__(name)
        self.init_state("IDLE")
        self.insert_state("IDLE", 1)

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        pass

    def output(self, msg_deliver):
        pass

def test_new_feature():
    model = TestModel("test")
    # Test implementation
    assert expected_result
```

### 4. Documentation Phase
- Add docstrings to all public methods
- Update CLAUDE.md if architecture changes
- **NEVER** create new README or docs unless explicitly requested

## Common Patterns

### Message Handling
```python
# Creating messages
msg = SysMessage(source_name, port_name)
msg.insert(data)  # Single item
msg.extend([data1, data2])  # Multiple items

# In output function
def output(self, msg_deliver):
    msg = SysMessage(self.get_name(), "port_out")
    msg.insert(data)
    msg_deliver.insert_message(msg)
    return msg_deliver
```

### State Management
```python
# Define states in __init__
self.insert_state("STATE_NAME", deadline_float)
self.init_state("INITIAL_STATE")

# Transition states
self._cur_state = "NEW_STATE"

# Update deadlines dynamically
self.update_state("STATE_NAME", new_deadline)
```

### Port Coupling
```python
# In SysExecutor
se.coupling_relation(src_model, "out_port", dst_model, "in_port")

# In StructuralModel
sm.coupling_relation(src_model, "out_port", dst_model, "in_port")
```

### Snapshot/Restore
```python
# Setup with snapshot capability
from pyjevsim.snapshot_manager import SnapshotManager

sm = SnapshotManager()
se = SysExecutor(time_resolution, "sim_name", snapshot_manager=sm)

# Take snapshot
se.snapshot_simulation(name="snapshot_name", directory_path="./snapshots")

# Restore
from pyjevsim.restore_handler import RestoreHandler
rh = RestoreHandler()
rh.restore_simulation(se, "snapshot_name", "./snapshots")
```

## Performance Considerations

### Optimization Guidelines
1. **Event Scheduling**: Use heap-based priority queue (already implemented)
2. **Object Lifecycle**: Prefer heap-based tracking for creation/destruction
3. **Port Mapping**: Use dict lookups (O(1)) over list scans
4. **Message Delivery**: Batch messages via MessageDeliverer
5. **Avoid**: Linear scans through large collections in hot paths

### Time Complexity Targets
- Event scheduling: O(log n)
- Port message routing: O(1) average
- Model creation/destruction: O(log n)
- Snapshot operation: O(n) acceptable

## Dependencies

### Required
- **dill ~= 0.3.6**: Model serialization (snapshot/restore)
- Python 3.10+

### Optional
- **pytest**: Testing framework

### Installation
```bash
pip install -r requirements.txt
```

## Snapshot System Architecture

### Components
1. **SnapshotManager**: Coordinates snapshot operations
2. **SnapshotExecutor**: Wraps executors to enable state capture
3. **SnapshotFactory**: Creates snapshot-enabled executors
4. **RestoreHandler**: Reconstructs simulation from snapshots

### Serialization Rules
- Use `dill` for deep serialization
- **MUST** be serializable: All model state, ports, couplings
- **CANNOT** serialize: Thread locks, file handles, sockets
- Test snapshot/restore in dedicated test cases

## Error Handling

### Common Error Patterns
```python
# Input validation
if param < 0:
    raise ValueError(f"Parameter must be positive, got {param}")

# State validation
if state_name not in self._states:
    raise KeyError(f"State '{state_name}' not found")

# Port validation
if port not in self.external_input_ports:
    print(f"[ERROR] Port '{port}' not found")
    raise AssertionError
```

## Anti-Patterns to Avoid

### ❌ DON'T
- Modify `global_time` outside simulation engine
- Create circular coupling (A→B→A without proper termination)
- Skip executor factory (directly instantiate executors)
- Use interactive git commands (`git add -i`, `git rebase -i`)
- Create documentation files without explicit request
- Add emojis unless requested
- Violate DEVS execution order (output before transition)

### ✅ DO
- Use factory pattern for model/executor creation
- Validate all inputs at boundaries
- Follow DEVS semantics strictly
- Write comprehensive tests
- Use type hints and docstrings
- Keep examples simple and focused
- Profile performance for optimization features

## Git Workflow

### Commit Guidelines
- **NEVER** update git config
- **NEVER** use `--force`, `--no-verify`, `--amend` without explicit request
- Use descriptive commit messages (1-2 sentences)
- Format: `<type>: <description>` (e.g., "feat: add parallel scheduling")

### Branch Strategy
- Feature branches: `feature/<feature-name>`
- Bug fixes: `bugfix/<issue-name>`
- Main branch: `main`

## License and Attribution
- Author: Changbeom Choi (@cbchoi)
- Copyright: 2014-2020 Handong Global University, 2021-2024 Hanbat National University
- License: MIT
- **MUST** include license header in all new files

## Quick Reference

### Model Template
```python
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.system_message import SysMessage

class MyModel(BehaviorModel):
    def __init__(self, name):
        super().__init__(name)
        self.init_state("IDLE")
        self.insert_state("IDLE", float('inf'))
        self.insert_state("ACTIVE", 10)

        self.insert_input_port("in_port")
        self.insert_output_port("out_port")

    def ext_trans(self, port, msg):
        if port == "in_port":
            self._cur_state = "ACTIVE"

    def int_trans(self):
        self._cur_state = "IDLE"

    def output(self, msg_deliver):
        if self._cur_state == "ACTIVE":
            msg = SysMessage(self.get_name(), "out_port")
            msg.insert(data)
            msg_deliver.insert_message(msg)
        return msg_deliver
```

### Simulation Setup
```python
from pyjevsim.system_executor import SysExecutor
from pyjevsim.definition import ExecutionType, Infinite

# Create executor
se = SysExecutor(time_resolution=1, _sim_name="my_sim",
                 ex_mode=ExecutionType.V_TIME)

# Register models
se.register_entity(model1)
se.register_entity(model2)

# Couple models
se.coupling_relation(model1, "out", model2, "in")

# Add external ports
se.insert_input_port("external_in")
se.coupling_relation(se, "external_in", model1, "in")

# Run simulation
se.simulate(time=100)

# Get results
events = se.get_generated_event()
```

---

**Remember**
1. This is a DEVS simulation framework. Correctness of DEVS semantics is more important than feature velocity. When in doubt, consult DEVS formalism literature.
2. Rigorously keep correctness. 
