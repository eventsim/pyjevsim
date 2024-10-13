"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
from .executor_factory import ExecutorFactory
from .snapshot_executor import SnapshotExecutor

class SnapshotFactory(ExecutorFactory): 
    def __init__(self, snapshot_map):
        super().__init__()
        
        self.snapshot_condition_map = snapshot_map
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
        model = super().create_executor(global_time, ins_t, des_t, en_name, model)
        
        return self.create_snapshot_executor(model)
    
    def create_snapshot_executor(self, model):
        if model.get_name() in self.snapshot_condition_map:
            return SnapshotExecutor(model, self.snapshot_condition_map[model.get_name()](model))
        else:
            return model