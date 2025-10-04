"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT. The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Integration tests for DoEManager.
"""

import pytest
from pyjevsim.doe_manager import DoEManager
from pyjevsim.termination_condition import TimeBasedTermination, AttributeBasedTermination
from pyjevsim.system_executor import SysExecutor
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType


class SimpleGenerator(BehaviorModel):
    """Simple generator model for testing."""

    def __init__(self, name):
        super().__init__(name)
        self.generated_count = 0
        self.init_state("GEN")
        self.insert_state("GEN", 1)

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        self.generated_count += 1

    def output(self, msg_deliver):
        return msg_deliver


class SimpleDoE(DoEManager):
    """Simple DoE implementation for testing."""

    def __init__(self, num_replications, max_time):
        super().__init__(
            num_replications=num_replications,
            termination_condition=TimeBasedTermination(max_time),
            time_resolution=1.0
        )
        self.max_time = max_time

    def setup_models(self, executor: SysExecutor, replication_idx: int):
        """Setup a simple generator model."""
        gen = SimpleGenerator(f"gen_{replication_idx}")
        executor.register_entity(gen)

    def collect_data(self, executor: SysExecutor, replication_idx: int):
        """Collect generation count."""
        model = executor.get_model(f"gen_{replication_idx}")
        return {
            "replication": replication_idx,
            "final_time": executor.get_global_time(),
            "generated_count": model.generated_count
        }


def test_doe_basic_run():
    """Test basic DoE execution with multiple replications."""
    doe = SimpleDoE(num_replications=3, max_time=10)
    results = doe.run_experiment()

    assert results["num_replications"] == 3
    assert len(results["replication_data"]) == 3

    for i, data in enumerate(results["replication_data"]):
        assert data["replication"] == i
        assert data["final_time"] == 10
        # Generator increments at int_trans, terminates when time >= 10
        # So it generates during times 0-9, which is 9 or 10 items
        assert data["generated_count"] >= 9
        assert data["generated_count"] <= 10


def test_doe_simulation_isolation():
    """Test that replications are isolated (no state leakage)."""

    class StatefulDoE(DoEManager):
        def __init__(self):
            super().__init__(
                num_replications=3,
                termination_condition=TimeBasedTermination(5)
            )
            self.model_counts = []

        def setup_models(self, executor: SysExecutor, replication_idx: int):
            gen = SimpleGenerator("gen")
            executor.register_entity(gen)

        def collect_data(self, executor: SysExecutor, replication_idx: int):
            # Count how many models are registered
            model_count = len(executor.model_map)
            self.model_counts.append(model_count)

            return {
                "replication": replication_idx,
                "model_count": model_count
            }

    doe = StatefulDoE()
    results = doe.run_experiment()

    # Each replication should have same model count (gen + default message catcher)
    # This verifies simulation_stop() properly clears state
    assert all(count == doe.model_counts[0] for count in doe.model_counts)


def test_doe_custom_aggregation():
    """Test custom aggregation of results."""

    class AggregatingDoE(SimpleDoE):
        def aggregate_results(self):
            counts = [d["generated_count"] for d in self.replication_data]
            return {
                "num_replications": self.num_replications,
                "mean_count": sum(counts) / len(counts),
                "max_count": max(counts),
                "min_count": min(counts),
                "raw_data": self.replication_data
            }

    doe = AggregatingDoE(num_replications=5, max_time=10)
    results = doe.run_experiment()

    assert "mean_count" in results
    assert "max_count" in results
    assert "min_count" in results
    # All should generate 9-10 (off-by-one depends on DEVS semantics)
    assert 9 <= results["mean_count"] <= 10
    assert 9 <= results["min_count"] <= 10
    assert 9 <= results["max_count"] <= 10


def test_doe_parametric_sweep():
    """Test parametric sweep with different configurations."""

    class ParametricDoE(DoEManager):
        def __init__(self, time_values):
            super().__init__(
                num_replications=len(time_values),
                termination_condition=TimeBasedTermination(max(time_values))
            )
            self.time_values = time_values

        def setup_models(self, executor: SysExecutor, replication_idx: int):
            gen = SimpleGenerator(f"gen_{replication_idx}")
            executor.register_entity(gen)

            # Store config in executor for this replication
            self._current_max_time = self.time_values[replication_idx]

        def collect_data(self, executor: SysExecutor, replication_idx: int):
            model = executor.get_model(f"gen_{replication_idx}")
            return {
                "replication": replication_idx,
                "max_time": self.time_values[replication_idx],
                "generated_count": model.generated_count
            }

        def _run_simulation(self, executor: SysExecutor):
            """Override to use per-replication time limit."""
            # Create custom termination for this replication
            custom_term = TimeBasedTermination(self._current_max_time)

            executor.init_sim()
            while not custom_term.should_terminate(executor):
                if executor.is_terminated():
                    break
                executor.schedule()

    doe = ParametricDoE(time_values=[5, 10, 15])
    results = doe.run_experiment()

    assert len(results["replication_data"]) == 3
    # Allow off-by-one due to DEVS semantics
    assert 4 <= results["replication_data"][0]["generated_count"] <= 5
    assert 9 <= results["replication_data"][1]["generated_count"] <= 10
    assert 14 <= results["replication_data"][2]["generated_count"] <= 15


def test_doe_attribute_based_termination():
    """Test DoE with attribute-based termination."""

    class AttributeDoE(DoEManager):
        def __init__(self, num_replications, max_count):
            super().__init__(
                num_replications=num_replications,
                termination_condition=AttributeBasedTermination(
                    "counter",
                    "generated_count",
                    lambda c: c >= max_count
                )
            )
            self.max_count = max_count

        def setup_models(self, executor: SysExecutor, replication_idx: int):
            gen = SimpleGenerator("counter")
            executor.register_entity(gen)

        def collect_data(self, executor: SysExecutor, replication_idx: int):
            model = executor.get_model("counter")
            return {
                "replication": replication_idx,
                "final_time": executor.get_global_time(),
                "generated_count": model.generated_count
            }

    doe = AttributeDoE(num_replications=3, max_count=7)
    results = doe.run_experiment()

    for data in results["replication_data"]:
        # Should terminate when count reaches 7
        assert data["generated_count"] >= 7
        # Time may be 7 or 8 depending on when condition is checked
        assert 7 <= data["final_time"] <= 8


def test_doe_invalid_num_replications():
    """Test DoEManager with invalid num_replications."""
    with pytest.raises(ValueError):
        SimpleDoE(num_replications=0, max_time=10)

    with pytest.raises(ValueError):
        SimpleDoE(num_replications=-5, max_time=10)


def test_doe_simulation_stop_cleanup():
    """Test that simulation_stop() properly cleans up between runs."""

    class CleanupCheckDoE(DoEManager):
        def __init__(self):
            super().__init__(
                num_replications=2,
                termination_condition=TimeBasedTermination(5)
            )
            self.cleanup_checks = []

        def setup_models(self, executor: SysExecutor, replication_idx: int):
            # Add multiple models
            for i in range(3):
                gen = SimpleGenerator(f"gen{i}")
                executor.register_entity(gen)

            # Add coupling
            executor.insert_input_port("test_port")

        def collect_data(self, executor: SysExecutor, replication_idx: int):
            # Before cleanup, executor should have models
            before_cleanup = {
                "model_count": len(executor.model_map),
                "port_count": len(executor.port_map),
                "active_count": len(executor.active_obj_map)
            }

            return {
                "replication": replication_idx,
                "before_cleanup": before_cleanup
            }

    doe = CleanupCheckDoE()
    results = doe.run_experiment()

    # All replications should have same initial state
    for data in results["replication_data"]:
        # Should have 3 gens + 1 default message catcher = 4 models
        assert data["before_cleanup"]["model_count"] == 4


def test_doe_load_model_from_file():
    """Test loading model from factory function."""

    def model_factory():
        return SimpleGenerator("factory_gen")

    class FactoryDoE(DoEManager):
        def __init__(self):
            super().__init__(
                num_replications=2,
                termination_condition=TimeBasedTermination(5)
            )

        def setup_models(self, executor: SysExecutor, replication_idx: int):
            # Load model using factory
            gen = self.load_model_from_file(model_factory)
            executor.register_entity(gen)

        def collect_data(self, executor: SysExecutor, replication_idx: int):
            model = executor.get_model("factory_gen")
            return {
                "replication": replication_idx,
                "count": model.generated_count
            }

    doe = FactoryDoE()
    results = doe.run_experiment()

    assert len(results["replication_data"]) == 2
    for data in results["replication_data"]:
        # Allow off-by-one
        assert 4 <= data["count"] <= 5


def test_doe_current_replication_tracking():
    """Test that current_replication is properly updated."""

    class ReplicationTracker(SimpleDoE):
        def __init__(self):
            super().__init__(num_replications=3, max_time=5)
            self.tracked_indices = []

        def setup_models(self, executor: SysExecutor, replication_idx: int):
            super().setup_models(executor, replication_idx)
            self.tracked_indices.append((self.current_replication, replication_idx))

    doe = ReplicationTracker()
    doe.run_experiment()

    # Verify current_replication matches replication_idx
    for current, idx in doe.tracked_indices:
        assert current == idx
