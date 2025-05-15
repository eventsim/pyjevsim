"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

"""
from dill import load, loads
from .definition import ModelType, ExecutionType
import json
import ast
from .system_executor import SysExecutor

class RestoreHandler():
    """ Restore a snapshotted model or project.
    """
    def __init__(self, t_resol=1, ex_mode=ExecutionType.V_TIME, name="project", path="./snapshot"):
        """
        Initializes the RestoreHandler with time resolution, execution mode, name, and path.

        Args:
            t_resol (float): Time resolution
            ex_mode (R_TIME or V_TIME): Execution mode(Real time or Virtual time)
            name (str): Name of SysExecutor
            path (str, optional): Path to load snapshots
        """
        self.path = f"{path}/{name}"
        self.sim_name = name
        self.engine = SysExecutor(t_resol, name, ex_mode, snapshot_manager=None)
        self.model_map = {}
        pass
        
    def restore_engine(self):
        """
        Sets up SysExecutor with the relation map and model map.
        """
        with open(f"{self.path}/relation_map.json", "r") as f:
            relation = json.load(f)   
        relation = {ast.literal_eval(key): ast.literal_eval(value) for key, value in relation.items()}

        model_list = {}
        with open(f"{self.path}/model_map.json", "r") as f:
            model_list = json.load(f)  
        model_list = model_list["model_name"]

        self.load_models(model_list)
        self.relations(relation)

    def load_models(self, model_list):
        """
        Loads models from files and registers them with SysExecutor.
        
        Args:
            model_list (list): List of model names
        """
        for model_name in model_list:
            with open(f"{self.path}/{model_name}.simx", "rb") as f:
                model = load(f)
            
            self.model_map[model_name] = model["data"]
            self.engine.register_entity(model["data"])

    def relations(self, relation_map):
        """
        Sets up coupling relations in SysExecutor.
        
        Args:
            relation_map (dict): The relation map / 관계 맵
        """
        for key, value in relation_map.items():
            if key[0] in self.model_map.keys():
                output_model = self.model_map[key[0]]
            else:
                output_model = self.engine
            for model in value:
                if model[0]:
                    input_model = self.model_map[model[0]]
                else:
                    input_model = self.engine
                self.engine.coupling_relation(output_model, key[1], input_model, model[1])

    def get_engine(self):
        """Returns the SysExecutor.

        Returns:
            Restored SysExecutor
        """
        self.restore_engine()
        return self.engine
    
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
        
        if model_info["type"] != ModelType.BEHAVIORAL and model_info["type"] != ModelType.STRUCTURAL :
            raise Exception(f"{model_info['name']} is not of Model type")
        
        model = model_info["data"]
                    
        if name is not None:
            model.set_name(name)
            
        return model
    