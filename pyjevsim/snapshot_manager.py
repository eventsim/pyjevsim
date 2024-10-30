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
    """SnapshotManager performs snapshots or restores snapshotted data.
    It manages the models you want to snapshot and the SnapshotCondition for those models. 
    It snapshots simulations (the directory where all the models and their releases are stored).
    It also manages the RestoreHandler, which performs a restore of the model or simulation. 
    """
    def __init__(self,  restore_handler = None):
        """
        Args:
            restore_handler (RestoreHandler, optional): If you want to restore snapshotted simulation, specify a RestoreHandler as a parameter. Defaults to None.
        """
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
        """Associate the model you want to take a snapshot of with the model's SnapshotCondition.

        Args:
            _name (str): BehaivorModel name
            _snapshot_condition (SnapshotCondition): Concrete SnapshotCondition
        """
        self.snapshot_condition_map[_name] = _snapshot_condition
        
    def get_snapshot_factory(self):
        """Creates a SnapshotFactory with the SnapshotConditions entered by the user.

        Returns:
            SnapshotFactory: SnapshotFactory that generates a SnapshotExecutor that takes the snapshot 
        """
        return SnapshotFactory(self.snapshot_condition_map)
    
    def load_snapshot(self, name, shotmodel):
        """_summary_

        Args:
            name (str): The name of the snapshot Model to restore.
            shotmodel (Binary): Data from snapshotted models.

        Returns:
            restore_handler.load_snapshot(name, shotmodel) : Restored BehaviorModel
        """
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