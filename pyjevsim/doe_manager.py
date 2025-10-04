"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT. The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module provides Design of Experiments (DoE) management functionality for pyjevsim.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable

from .termination_condition import TerminationCondition
from .system_executor import SysExecutor
from .structural_model import StructuralModel
from .definition import ExecutionType


class DoEManager(ABC):
    """
    Abstract base class for Design of Experiments management.

    Users should inherit from this class and implement:
    - setup_models(): Configure models for each run
    - collect_data(): Extract data from completed simulation
    - aggregate_results(): Combine data from all runs (optional)
    """

    def __init__(self,
                 num_replications: int,
                 termination_condition: TerminationCondition,
                 time_resolution: float = 1.0,
                 execution_mode: ExecutionType = None):
        """
        Initialize DoE Manager.

        Args:
            num_replications (int): Number of simulation runs to execute
            termination_condition (TerminationCondition): Termination criteria
            time_resolution (float): Simulation time resolution
            execution_mode (ExecutionType): V_TIME or R_TIME

        Raises:
            ValueError: If num_replications < 1
        """
        if num_replications < 1:
            raise ValueError(f"num_replications must be >= 1, got {num_replications}")

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
            NotImplementedError: Snapshot restoration integration pending
        """
        if not self.snapshot_manager:
            raise ValueError("Snapshot manager not set. Call set_snapshot_manager() first.")

        from .restore_handler import RestoreHandler
        rh = RestoreHandler()
        # TODO: Implement snapshot restoration for DoE
        # This requires integration with existing snapshot system
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

        This method orchestrates multiple simulation runs:
        1. Creates fresh SysExecutor for each replication
        2. Calls user's setup_models() to configure simulation
        3. Runs simulation until termination condition
        4. Calls user's collect_data() to extract results
        5. Cleans up executor with simulation_stop()
        6. Aggregates all results

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
