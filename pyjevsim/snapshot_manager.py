from abc import abstractmethod
from dill import load
from .definition import ModelType
import json
import os
import ast
from .system_executor import SysExecutor

class SnapshotManager : 
    def __init__(self, t_resol, ex_mode, name, path = ".") :
        self.path = f"{path}/{name}"
        self.sim_name = name
        self.engine = SysExecutor(t_resol, ex_mode, snapshot_manager=None)
        self.model_map = {}
        self.set_engine()
        pass
    
    def set_engine(self) :
        with open(f"{self.path}/relation_map.json", "r") as f :
            relation = json.load(f)   
        relation = {ast.literal_eval(key): ast.literal_eval(value) for key, value in relation.items()}

        model_list = {}
        with open(f"{self.path}/model_map.json", "r") as f :
            model_list = json.load(f)  
        model_list = model_list["model_name"]

        self.load_models(model_list)
        self.relations(relation)
    
    def load_models(self, model_list) :
        for model_name in model_list : 
            with open(f"{self.path}/{model_name}.simx", "rb") as f:
                model = load(f)
            self.model_map[model_name] = model
            self.engine.register_entity(model)

    def relations(self, relation_map) :
        for key, value in relation_map.items() :
            if key[0] :
                output_model = self.model_map[key[0]]
            else : 
                output_model = self.engine
            for model in value : 
                if model[0] : 
                    input_model = self.model_map[model[0]]
                else : 
                    input_model = self.engine
                self.engine.coupling_relation(output_model, key[1], input_model, model[1])
    
    def get_engine(self) :
        return self.engine
                
