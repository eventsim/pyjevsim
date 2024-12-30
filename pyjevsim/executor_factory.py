"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains an ExecutorFactory that decorates an object of type Model into an Executor that is executable by a SysExecutor. 
"""

from .definition import ModelType
from .behavior_executor import BehaviorExecutor
from .structural_executor import StructuralExecutor

class ExecutorFactory:
    """Factory class to create different types of executors."""
    
    def __init__(self):
        pass

    def create_executor(self, global_time, ins_t, des_t, en_name, model, parent
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
                global_time, ins_t, des_t, en_name, model, parent
            )
        elif model.get_model_type() == ModelType.STRUCTURAL:
            return self.create_structural_executor(
                global_time, ins_t, des_t, en_name, model, parent
            )
        else:
            return None

    def create_behavior_executor(self, _, ins_t, des_t, en_name, model, parent):
        """Create BehaviorModelexecutor

        Args:
            _ (float): Unused global time
            ins_t (float): Instance creation time 
            des_t (float): Destruction time
            en_name (str): SysExecutor name 
            model (BehaviorModel): Behavior model to execute

        Returns:
            BehaviorModelExecutor: The created BehaviorModelexecutor
        """
        return BehaviorExecutor(ins_t, des_t, en_name, model, parent)

    def create_structural_executor(self, global_time, ins_t, des_t, en_name, model, parent):
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
        return StructuralExecutor(
            global_time, ins_t, des_t, en_name, model, parent, self 
        )
    