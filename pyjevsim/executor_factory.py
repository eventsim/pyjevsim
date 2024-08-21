"""
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""

from .behavior_model_executor import BehaviorModelExecutor
from .definition import ModelType
from .structural_executor_model import StructuralModelExecutor
from .snapshot_executor import SnapshotExecutor

class ExecutorFactory:
    """Factory class to create different types of executors."""
    
    def __init__(self):
        pass

    def create_executor(
        self,
        global_time,
        ins_t,
        des_t,
        en_name,
        model,
    ):
        """Creates an executor based on the model type.

        Args:
            global_time (float): Global simulation time
            ins_t (float): Instance creation time
            des_t (float): Destruction time
            en_name (str): Engine name
            model(ModelType.BEHAVIORAL of ModelType.STRUCTURAL): The model to execute

        Returns:
            Executor: The created executor
        """
        if model.get_model_type() == ModelType.BEHAVIORAL:
            return self.create_behavior_executor(
                global_time, ins_t, des_t, en_name, model
            )
        elif model.get_model_type() == ModelType.STRUCTURAL:
            return self.create_structural_executor(
                global_time, ins_t, des_t, en_name, model
            )
        else:
            return None

    def create_behavior_executor(self, _, ins_t, des_t, en_name, model):
        """Create BehaviorModelexecutor

        Args:
            _ (float): Unused global time
            ins_t (float): Instance creation time 
            des_t (float): Destruction time
            en_name (str): SysExecutor name / 엔진 이름
            model (BehaviorModel): Behavior model to execute / 실행할 동작 모델

        Returns:
            BehaviorModelExecutor: The created BehaviorModelexecutor
        """
        return BehaviorModelExecutor(ins_t, des_t, en_name, model)

    def create_structural_executor(self, global_time, ins_t, des_t, en_name, model):
        """Create StructuralModelExecutor

        Args:
            global_time (float): Global simulation time
            ins_t (float): Instance creation time 
            des_t (float): Destruction time
            en_name (str): SysExecutor name
            model (StructuralModel): StructuralModel to execute

        Returns:
            StructuralModelExecutor: created StructuralModelExecutor 
        """
        return StructuralModelExecutor(
            global_time, ins_t, des_t, en_name, model, self.create_behavior_executor
        )

    def create_snapshot_behavior_executor(self, _, ins_t, des_t, en_name, model, snapshot_condition):
        """
        Create SnapshotExecutor.
        The SnapshotExecutor decorates a BehaviorModelExecutor to store data from a running BehaviorModel under certain conditions.

        Args:
            _ (float): Unused global time
            ins_t (float): Instance creation time
            des_t (float): Destruction time
            en_name (str): SysExecutor name
            model (BehaviorModel): The behavior model to execute
            snapshot_condition (Callable): The condition to take snapshots

        Returns:
            SnapshotExecutor: The created SnapshotExecutor
        """
        return SnapshotExecutor(ins_t, des_t, en_name, model, snapshot_condition)
    