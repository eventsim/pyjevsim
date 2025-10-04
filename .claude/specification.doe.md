# Design of Experiments (DoE) Feature Specification

## Overview
This specification defines the Design of Experiments (DoE) feature for pyjevsim, enabling systematic execution of multiple simulation runs with different configurations, termination conditions, and data collection strategies.

## Motivation
Currently, pyjevsim users must manually implement repetitive simulation execution logic (see `examples/banksim/banksim.py`). The DoE feature provides a standardized framework for:
- Running multiple simulation replications
- Managing model configurations across runs
- Defining custom termination conditions
- Collecting and aggregating experimental data
- Supporting model restoration from snapshots or Python files

## Architecture Overview

```
+-------------------------------------------------------------+
|                        DoEManager                           |
|  - Experiment configuration                                 |
|  - Model factory (snapshot/Python)                          |
|  - Data collection strategy                                 |
|  - Replication orchestration                                |
+----------------+--------------------------------------------+
                 |
                 | Creates/Configures
                 |
+----------------v--------------------------------------------+
|                    SysExecutor                              |
|  - Receives TerminationCondition                            |
|  - Registers models from DoEManager                         |
|  - Executes simulation with custom termination             |
|  - Calls simulation_stop() between runs                     |
+----------------+--------------------------------------------+
                 |
                 | Evaluates
                 |
+----------------v--------------------------------------------+
|              TerminationCondition                           |
|  - User-defined termination logic                           |
|  - Time-based or model attribute-based                      |
+-------------------------------------------------------------+
```

## Core Components

### 1. TerminationCondition (Abstract Base Class)

**Purpose**: Define custom termination criteria beyond simple time limits.

**Location**: `pyjevsim/termination_condition.py`

**Interface**:
```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .system_executor import SysExecutor

class TerminationCondition(ABC):
    """Abstract base class for simulation termination conditions."""

    @abstractmethod
    def should_terminate(self, executor: 'SysExecutor') -> bool:
        """
        Determines if the simulation should terminate.

        Args:
            executor (SysExecutor): The simulation executor

        Returns:
            bool: True if simulation should terminate, False otherwise
        """
        pass

    def on_terminate(self, executor: 'SysExecutor') -> None:
        """
        Optional callback when termination condition is met.

        Args:
            executor (SysExecutor): The simulation executor
        """
        pass
```

**Built-in Implementations**:

```python
class TimeBasedTermination(TerminationCondition):
    """Terminates simulation after specified time."""

    def __init__(self, max_time: float):
        self.max_time = max_time

    def should_terminate(self, executor: 'SysExecutor') -> bool:
        return executor.get_global_time() >= self.max_time


class AttributeBasedTermination(TerminationCondition):
    """Terminates when model attribute meets condition."""

    def __init__(self, model_name: str, attribute_path: str,
                 condition_fn: callable):
        """
        Args:
            model_name (str): Name of model to monitor
            attribute_path (str): Dot-separated path to attribute
            condition_fn (callable): Function(value) -> bool
        """
        self.model_name = model_name
        self.attribute_path = attribute_path
        self.condition_fn = condition_fn

    def should_terminate(self, executor: 'SysExecutor') -> bool:
        try:
            model = executor.get_model(self.model_name)
            value = self._get_nested_attribute(model, self.attribute_path)
            return self.condition_fn(value)
        except (KeyError, AttributeError):
            return False

    def _get_nested_attribute(self, obj, path: str):
        """Navigate nested attributes using dot notation."""
        attrs = path.split('.')
        for attr in attrs:
            obj = getattr(obj, attr)
        return obj


class CompositeTermination(TerminationCondition):
    """Combines multiple termination conditions with AND/OR logic."""

    def __init__(self, conditions: list, mode: str = "OR"):
        """
        Args:
            conditions (list[TerminationCondition]): Conditions to combine
            mode (str): "AND" or "OR"
        """
        self.conditions = conditions
        self.mode = mode.upper()

        if self.mode not in ["AND", "OR"]:
            raise ValueError("mode must be 'AND' or 'OR'")

    def should_terminate(self, executor: 'SysExecutor') -> bool:
        if self.mode == "AND":
            return all(c.should_terminate(executor) for c in self.conditions)
        else:  # OR
            return any(c.should_terminate(executor) for c in self.conditions)
```

### 2. DoEManager (Abstract Base Class)

**Purpose**: Orchestrate multiple simulation runs with configuration, data collection, and model management.

**Location**: `pyjevsim/doe_manager.py`

**Interface**:
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from .termination_condition import TerminationCondition
from .system_executor import SysExecutor
from .structural_model import StructuralModel

class DoEManager(ABC):
    """
    Abstract base class for Design of Experiments management.

    Users should inherit from this class and implement:
    - setup_models(): Configure models for each run
    - collect_data(): Extract data from completed simulation
    - aggregate_results(): Combine data from all runs
    """

    def __init__(self,
                 num_replications: int,
                 termination_condition: TerminationCondition,
                 time_resolution: float = 1.0,
                 execution_mode: 'ExecutionType' = None):
        """
        Initialize DoE Manager.

        Args:
            num_replications (int): Number of simulation runs to execute
            termination_condition (TerminationCondition): Termination criteria
            time_resolution (float): Simulation time resolution
            execution_mode (ExecutionType): V_TIME or R_TIME
        """
        if num_replications < 1:
            raise ValueError("num_replications must be >= 1")

        self.num_replications = num_replications
        self.termination_condition = termination_condition
        self.time_resolution = time_resolution
        self.execution_mode = execution_mode or ExecutionType.V_TIME

        # Data storage
        self.replication_data = []  # List of data from each run
        self.current_replication = 0

        # Optional snapshot manager
        self.snapshot_manager = None

    @abstractmethod
    def setup_models(self, executor: SysExecutor, replication_idx: int) -> None:
        """
        Configure and register models for a simulation run.

        This method is called before each replication. Implement model
        creation, registration, and coupling here.

        Args:
            executor (SysExecutor): The simulation executor
            replication_idx (int): Current replication number (0-indexed)
        """
        pass

    @abstractmethod
    def collect_data(self, executor: SysExecutor, replication_idx: int) -> Dict[str, Any]:
        """
        Collect data from a completed simulation run.

        Args:
            executor (SysExecutor): The simulation executor
            replication_idx (int): Current replication number (0-indexed)

        Returns:
            Dict[str, Any]: Data collected from this replication
        """
        pass

    def aggregate_results(self) -> Dict[str, Any]:
        """
        Aggregate results from all replications.

        Default implementation returns raw data. Override for custom
        aggregation (mean, std, percentiles, etc.).

        Returns:
            Dict[str, Any]: Aggregated results
        """
        return {
            "num_replications": self.num_replications,
            "replication_data": self.replication_data
        }

    def set_snapshot_manager(self, snapshot_manager: 'SnapshotManager') -> None:
        """
        Set snapshot manager for model restoration.

        Args:
            snapshot_manager (SnapshotManager): The snapshot manager
        """
        self.snapshot_manager = snapshot_manager

    def load_model_from_snapshot(self, snapshot_name: str,
                                 directory: str = ".") -> StructuralModel:
        """
        Load a model from snapshot for use in experiments.

        Args:
            snapshot_name (str): Name of the snapshot
            directory (str): Directory containing snapshots

        Returns:
            StructuralModel: Restored model

        Raises:
            ValueError: If snapshot manager is not set
        """
        if not self.snapshot_manager:
            raise ValueError("Snapshot manager not set. Call set_snapshot_manager() first.")

        from .restore_handler import RestoreHandler
        rh = RestoreHandler()
        # Restore logic - returns model
        # Implementation depends on snapshot system design
        raise NotImplementedError("Snapshot restoration for DoE pending implementation")

    def load_model_from_file(self, model_factory: Callable[[], Any]) -> Any:
        """
        Load a model using a factory function.

        Args:
            model_factory (Callable): Function that creates and returns a model

        Returns:
            Model instance
        """
        return model_factory()

    def run_experiment(self) -> Dict[str, Any]:
        """
        Execute the full design of experiments.

        Returns:
            Dict[str, Any]: Aggregated experimental results
        """
        print(f"[DoE] Starting experiment: {self.num_replications} replications")

        for i in range(self.num_replications):
            self.current_replication = i
            print(f"[DoE] Running replication {i+1}/{self.num_replications}")

            # Create fresh executor for this replication
            executor = SysExecutor(
                self.time_resolution,
                _sim_name=f"doe_run_{i}",
                ex_mode=self.execution_mode,
                snapshot_manager=self.snapshot_manager
            )

            # User-defined model setup
            self.setup_models(executor, i)

            # Run simulation with custom termination
            self._run_simulation(executor)

            # User-defined data collection
            data = self.collect_data(executor, i)
            self.replication_data.append(data)

            # Clean up for next run
            executor.simulation_stop()

            print(f"[DoE] Replication {i+1} complete")

        print(f"[DoE] Experiment complete. Aggregating results...")
        results = self.aggregate_results()

        return results

    def _run_simulation(self, executor: SysExecutor) -> None:
        """
        Run simulation until termination condition is met.

        Args:
            executor (SysExecutor): The simulation executor
        """
        executor.init_sim()

        while not self.termination_condition.should_terminate(executor):
            if executor.is_terminated():
                break
            executor.schedule()

        # Optional termination callback
        self.termination_condition.on_terminate(executor)
```

### 3. SysExecutor Modifications

**Changes Required**: Verify and enhance `simulation_stop()` for clean resets.

**Location**: `pyjevsim/system_executor.py`

**Enhanced `simulation_stop()` method**:
```python
def simulation_stop(self):
    """
    Stops the simulation and resets SysExecutor to initial state.

    This method ensures complete cleanup for Design of Experiments,
    allowing multiple simulation runs with the same executor instance.
    """
    # Reset time
    self.global_time = 0
    self.target_time = 0

    # Clear object maps
    self.waiting_obj_map = {}
    self._waiting_heap = []
    self.active_obj_map = {}
    self._destruction_heap = []

    # Clear port mappings
    self.port_map = {}
    self.product_port_map = {}

    # Clear model registry
    self.model_map = {}
    self.hierarchical_structure = {}

    # Reset schedule queue
    self._schedule_queue = ScheduleQueue()

    # Clear event queues
    with self.lock:
        self.input_event_queue = []
    self.output_event_queue.clear()

    # Reset simulation mode
    self.simulation_mode = SimulationMode.SIMULATION_IDLE

    # Reset timestamp
    self.sim_init_time = datetime.datetime.now()

    # Re-register default message catcher
    self.dmc = DefaultMessageCatcher("dc")
    self.register_entity(self.dmc)
```

**New method for DoE integration**:
```python
def simulate_with_condition(self, termination_condition: TerminationCondition,
                           _tm: bool = True) -> None:
    """
    Run simulation with custom termination condition.

    Args:
        termination_condition (TerminationCondition): Custom termination logic
        _tm (bool): Whether to use termination manager for signal handling
    """
    if _tm:
        self.tm = TerminationManager()

    self.init_sim()

    while not termination_condition.should_terminate(self):
        if self.is_terminated():
            break
        self.schedule()

    termination_condition.on_terminate(self)
```

## Usage Examples

### Example 1: Basic Time-Based DoE

```python
from pyjevsim.doe_manager import DoEManager
from pyjevsim.termination_condition import TimeBasedTermination
from pyjevsim.system_executor import SysExecutor
from examples.banksim.model.model_user_gen import BankUserGenerator
from examples.banksim.model.model_queue import BankQueue
from examples.banksim.model.model_accountant import BankAccountant

class BankSimDoE(DoEManager):
    def __init__(self, num_replications: int, sim_time: float):
        termination = TimeBasedTermination(sim_time)
        super().__init__(num_replications, termination)

        self.results = []

    def setup_models(self, executor: SysExecutor, replication_idx: int):
        # Create models
        gen = BankUserGenerator("gen")
        queue = BankQueue("queue", queue_size=10, proc_num=2)
        acc1 = BankAccountant("acc1", 0)
        acc2 = BankAccountant("acc2", 1)

        # Register
        executor.register_entity(gen)
        executor.register_entity(queue)
        executor.register_entity(acc1)
        executor.register_entity(acc2)

        # Couple
        executor.insert_input_port("start")
        executor.coupling_relation(None, "start", gen, "start")
        executor.coupling_relation(gen, "user_out", queue, "user_in")
        executor.coupling_relation(queue, "proc0", acc1, "in")
        executor.coupling_relation(queue, "proc1", acc2, "in")
        executor.coupling_relation(acc1, "next", queue, "proc_checked")
        executor.coupling_relation(acc2, "next", queue, "proc_checked")

        # Start
        executor.insert_external_event("start", None)

    def collect_data(self, executor: SysExecutor, replication_idx: int):
        queue_model = executor.get_model("queue")

        return {
            "replication": replication_idx,
            "final_time": executor.get_global_time(),
            "queue_length": len(queue_model.user_list),
            "dropped_users": queue_model.drop_count
        }

    def aggregate_results(self):
        import statistics

        dropped = [d["dropped_users"] for d in self.replication_data]

        return {
            "num_replications": self.num_replications,
            "mean_dropped": statistics.mean(dropped),
            "stdev_dropped": statistics.stdev(dropped) if len(dropped) > 1 else 0,
            "raw_data": self.replication_data
        }

# Run experiment
doe = BankSimDoE(num_replications=30, sim_time=1000)
results = doe.run_experiment()

print(f"Mean dropped users: {results['mean_dropped']:.2f}")
print(f"Stdev dropped users: {results['stdev_dropped']:.2f}")
```

### Example 2: Attribute-Based Termination

```python
from pyjevsim.termination_condition import AttributeBasedTermination

class BankSimWithMaxUsers(DoEManager):
    def __init__(self, num_replications: int, max_processed: int):
        # Terminate when 'result' model processes max_processed users
        termination = AttributeBasedTermination(
            model_name="result",
            attribute_path="processed_count",
            condition_fn=lambda count: count >= max_processed
        )
        super().__init__(num_replications, termination)
        self.max_processed = max_processed

    def setup_models(self, executor: SysExecutor, replication_idx: int):
        # Similar to Example 1, but include result model
        from examples.banksim.model.model_result import BankResult

        result = BankResult("result", self.max_processed)
        executor.register_entity(result)
        # ... rest of setup

    def collect_data(self, executor: SysExecutor, replication_idx: int):
        result_model = executor.get_model("result")

        return {
            "replication": replication_idx,
            "simulation_time": executor.get_global_time(),
            "processed_users": result_model.processed_count,
            "average_wait_time": result_model.get_average_wait_time()
        }
```

### Example 3: Composite Termination (Time OR Condition)

```python
from pyjevsim.termination_condition import (
    CompositeTermination,
    TimeBasedTermination,
    AttributeBasedTermination
)

# Terminate when EITHER:
# - 1000 time units elapsed
# - OR queue overflow count reaches 50
termination = CompositeTermination([
    TimeBasedTermination(1000),
    AttributeBasedTermination("queue", "drop_count", lambda x: x >= 50)
], mode="OR")

doe = BankSimDoE(num_replications=10, termination_condition=termination)
```

### Example 4: Parametric Sweep

```python
class ParametricBankSimDoE(DoEManager):
    def __init__(self, queue_sizes: List[int], replications_per_config: int):
        termination = TimeBasedTermination(1000)
        super().__init__(
            num_replications=len(queue_sizes) * replications_per_config,
            termination_condition=termination
        )

        self.queue_sizes = queue_sizes
        self.replications_per_config = replications_per_config

    def setup_models(self, executor: SysExecutor, replication_idx: int):
        # Determine configuration for this replication
        config_idx = replication_idx // self.replications_per_config
        queue_size = self.queue_sizes[config_idx]

        # Create models with specific queue size
        queue = BankQueue("queue", queue_size=queue_size, proc_num=2)
        # ... rest of setup

        # Store config for data collection
        executor._doe_config = {"queue_size": queue_size}

    def collect_data(self, executor: SysExecutor, replication_idx: int):
        queue_model = executor.get_model("queue")

        return {
            "replication": replication_idx,
            "config": executor._doe_config,
            "dropped_users": queue_model.drop_count
        }

    def aggregate_results(self):
        import statistics
        from collections import defaultdict

        by_config = defaultdict(list)

        for data in self.replication_data:
            queue_size = data["config"]["queue_size"]
            by_config[queue_size].append(data["dropped_users"])

        results = {}
        for queue_size, dropped_list in by_config.items():
            results[f"queue_{queue_size}"] = {
                "mean_dropped": statistics.mean(dropped_list),
                "stdev_dropped": statistics.stdev(dropped_list)
            }

        return results

# Run parametric sweep
doe = ParametricBankSimDoE(
    queue_sizes=[5, 10, 15, 20],
    replications_per_config=10
)
results = doe.run_experiment()
```

## Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Implement `TerminationCondition` abstract base class
- [ ] Implement `TimeBasedTermination`
- [ ] Implement `AttributeBasedTermination`
- [ ] Implement `CompositeTermination`
- [ ] Verify and enhance `SysExecutor.simulation_stop()`
- [ ] Add `SysExecutor.simulate_with_condition()`

### Phase 2: DoE Manager
- [ ] Implement `DoEManager` abstract base class
- [ ] Implement `run_experiment()` orchestration
- [ ] Add data collection and aggregation infrastructure
- [ ] Test replication isolation (no state leakage)

### Phase 3: Advanced Features
- [ ] Implement `load_model_from_snapshot()` integration
- [ ] Implement `load_model_from_file()` factory pattern
- [ ] Add progress callbacks/hooks
- [ ] Add result export (CSV, JSON)

### Phase 4: Testing & Documentation
- [ ] Unit tests for `TerminationCondition` classes
- [ ] Integration tests for `DoEManager`
- [ ] Test `simulation_stop()` cleanup
- [ ] Example: Basic DoE (banksim)
- [ ] Example: Parametric sweep
- [ ] Example: Snapshot-based DoE
- [ ] Update CLAUDE.md with DoE patterns

## Testing Strategy

### Unit Tests (`tests/test_doe_termination.py`)
```python
def test_time_based_termination():
    termination = TimeBasedTermination(100)
    # Mock executor with global_time
    # Assert termination at correct time

def test_attribute_based_termination():
    termination = AttributeBasedTermination(
        "model1", "counter", lambda x: x >= 10
    )
    # Mock executor and model
    # Assert termination when attribute condition met

def test_composite_termination_or():
    # Test OR logic

def test_composite_termination_and():
    # Test AND logic
```

### Integration Tests (`tests/test_doe_manager.py`)
```python
def test_doe_basic_run():
    # Simple DoE with 3 replications
    # Verify all replications execute
    # Verify data collection

def test_doe_simulation_isolation():
    # Verify state reset between runs
    # No leakage of models/events

def test_doe_parametric_sweep():
    # Parametric experiment
    # Verify correct configurations applied
```

### Regression Tests
```python
def test_simulation_stop_cleanup():
    # Verify all fields reset
    # Check event queues cleared
    # Verify model maps empty
```

## Design Decisions & Rationale

### 1. Abstract Base Classes
**Decision**: Use ABC for `DoEManager` and `TerminationCondition`

**Rationale**:
- Enforces implementation of critical methods
- Provides clear extension points for users
- Maintains consistency with existing pyjevsim patterns (e.g., `BehaviorModel`)

### 2. DoEManager Creates SysExecutor
**Decision**: DoEManager instantiates fresh `SysExecutor` per replication

**Rationale**:
- Guarantees clean state between runs
- Eliminates risk of state leakage
- Simplifies reasoning about experiments
- `simulation_stop()` serves as defensive cleanup, not primary reset

### 3. Separate Termination from Time
**Decision**: Decouple termination logic from `simulate(time=X)`

**Rationale**:
- Enables complex termination criteria (attributes, events, composites)
- Aligns with DoE needs (e.g., "run until 100 users processed")
- Backward compatible: `simulate(time=X)` unchanged

### 4. Data Collection in User Code
**Decision**: Users implement `collect_data()` instead of automatic instrumentation

**Rationale**:
- Avoids performance overhead of generic instrumentation
- Gives users full control over what data to extract
- Maintains DEVS formalism (no implicit observers)
- Simpler implementation

### 5. No Built-in Statistical Analysis
**Decision**: `aggregate_results()` returns raw data by default

**Rationale**:
- Avoids adding scipy/numpy dependencies
- Users have different statistical needs
- Easy to extend with custom aggregation
- Can recommend external tools (pandas, scipy)

## Future Enhancements

### V2: Parallel Execution
```python
class ParallelDoEManager(DoEManager):
    def run_experiment(self, num_workers: int = 4):
        # Use multiprocessing to run replications in parallel
        pass
```

### V3: Online Data Analysis
```python
class AdaptiveDoEManager(DoEManager):
    def should_continue_replications(self) -> bool:
        # Implement sequential stopping rules
        # E.g., stop when confidence interval narrow enough
        pass
```

### V4: Sensitivity Analysis
```python
class SensitivityDoEManager(DoEManager):
    def setup_latin_hypercube_sampling(self, parameters: Dict):
        # Generate LHS design
        pass
```

## Backward Compatibility

**Guarantee**: All existing pyjevsim code continues to work without modification.

- `SysExecutor.simulate(time=X)` unchanged
- No `DoEManager` required for single runs
- `simulation_stop()` safe to call (already exists)
- No new required dependencies

## License & Attribution

```python
"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT. The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module provides Design of Experiments functionality for pyjevsim.
"""
```

---

**Specification Status**: Draft v1.0
**Author**: Claude Code (based on user requirements)
**Date**: 2025-10-04
