from abc import abstractmethod
from dill import loads, dump
from .definition import ModelType
import json
import os

class ModelSnapshotManager:
    """Manager class for handling model snapshots."""
    def __init__(self):
        self.snapshot_executor_map = {} 
        self.load_snapshot_map = {}
    
    def snapshot_simulation(self, relation_map, model_map, name, directory_path="."):
        """
        Takes a snapshot of the simulation.
        Snapshot simulation model information and relationships to the “directory_path/name” location.
        
        Args:
            relation_map (dict): The relation map of SysExecutor
            model_map (dict): The model map of SysExecutor
            name (str): The name of Simulation
            directory_path (str): The directory path to save the snapshot
        """
        relation = {}
        for key, value in relation_map.items():
            if key[0]:
                port_key = ((key[0].get_name(), key[1]))
            else:
                port_key = key
                
            lst = []
            for model in value:
                if model[0] is not None:
                    data = (model[0].get_name(), model[1])
                    lst.append(tuple(data))
                else:
                    lst.append(model)
            relation[port_key] = lst
            
        path = f"{directory_path}/{name}"   
        if not os.path.exists(f"{path}"):
            os.makedirs(path)   
        
        with open(f"{path}/relation_map.json", "w") as f:
            relation = {str(key): str(value) for key, value in relation.items()}
            json.dump(relation, f)
        
        dump_model = {}
        with open(f"{path}/model_map.json", "w") as f:
            dump_model["model_name"] = list(model_map.keys())
            dump_model["model_name"].remove('dc')
            json.dump(dump_model, f)
            
        for key, value in model_map.items():
            if key == 'dc':
                continue
            with open(f"{path}/{key}.simx", "wb") as f:
                dump(value[0].get_core_model().model_snapshot(), f)
        return
    
    def register_snapshot_executor(self, name, snapshot_executor_generator):
        """
        Register SnapshotExecutor.
        
        Args:
            name (str): name of SnapshotExecutor / 스냅샷 실행기의 이름
            snapshot_executor_generator : The generator function for SnapshotExecutor
        """
        self.snapshot_executor_map[name] = snapshot_executor_generator
    
    def check_snapshot_executor(self, name):
        """Checks if a snapshot executor exists.
        
        Args:
            name (str): The name of SnapshotExecutor
        
        Returns:
            bool: True if exists, False otherwise
        """
        return name in self.snapshot_executor_map
    
    def create_snapshot_executor(self, behavior_executor):
        """
        Create SnapshotExecutor.

        Args:
            behavior_executor (BehaviorModelExecutor): BehaviorModelExecutor
        
        Returns:
            object: created SnapshotExecutor / 생성된 스냅샷 실행기
        """
        return self.snapshot_executor_map[behavior_executor.get_name()](behavior_executor)

    def load_snapshot(self, name, shotmodel):
        """Loads BehaviorModel.
        
        Args:
            name (str): The name of Model
            shotmodel (bytes): Binary data of the model snapshot
        
        Returns:
            object(BehaivorModel): The loaded model
        
        Raises:
            Exception: If the model type is not ModelType.BEHAVIORAL
        """
        model_info = loads(shotmodel)
        
        if model_info["type"] != ModelType.BEHAVIORAL:
            raise Exception(f"{model_info['name']} is not of BehaviorModel type")
        
        model = model_info["data"]
                    
        if name is not None:
            model.set_name(name)
            
        return model