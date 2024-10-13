"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains an object, SnapshotManager, that manages snapshots of the association between BehaivorModel and Model. 
"""

from dill import dump
import json
import os
from .snapshot_factory import SnapshotFactory

class SnapshotManager:
    """The ModelSnapshotManager reads the snapshotted simulation(the directory where all the models and their releases are stored) 
    and returns it as a SysExecutor."""
    def __init__(self,  restore_handler = None):
        self.snapshot_condition_map = {}
        self.restore_handler = restore_handler

    def get_engine(self):
        """Returns the SysExecutor.

        Returns:
            Restored SysExecutor
        """
        if self.restore_handler:
            return self.restore_handler.get_engine()
        else:
            return None
    
    def register_snapshot_condition(self, _name, _snapshot_condition):
        self.snapshot_condition_map[_name] = _snapshot_condition
        
    def get_snapshot_factory(self):
        return SnapshotFactory(self.snapshot_condition_map)
    
    def load_snapshot(self, name, shotmodel):
        if self.restore_handler:
            return self.restore_handler.load_snapshot(name, shotmodel)
        else:
            return None
    
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