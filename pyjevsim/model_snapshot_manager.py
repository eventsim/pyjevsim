from abc import abstractmethod
from dill import loads, dump
from .definition import ModelType
import json
import os
import ast

class ModelSnapshotManager :
    def __init__(self) :
        self.snapshot_executor_map = {}
        self.load_snapshot_map = {}
        pass
    
    def snapshot_simulation(self, relation_map, model_map, name, directory_path=".") :        
        relation = {}
        for key, value in relation_map.items() :
            if key[0] :
                port_key = ((key[0].get_name(), key[1]))
            else :
                port_key = key
                
            lst = []
            for model in value :
                if model[0] != None :
                    data = (model[0].get_name(), model[1])
                    lst.append(tuple(data))
                else :
                    lst.append(model)
            relation[port_key] = lst
            #print(relation)
            
        path = f"{directory_path}/{name}"   
        if not os.path.exists(f"{path}"):
            os.makedirs(path)   
        
        with open(f"{path}/relation_map.json", "w") as f :
            relation = {str(key): str(value) for key, value in relation.items()}
            json.dump(relation, f)
        
        dump_model = {}
        with open(f"{path}/model_map.json", "w") as f :
            dump_model["model_name"] = list(model_map.keys())
            dump_model["model_name"].remove('dc')
            json.dump(dump_model, f)
            
        for key, value in model_map.items() : 
            if key == 'dc' :
                continue
            with open(f"{path}/{key}.simx", "wb") as f :
                dump(value[0].get_core_model(), f)
        return
        
    def register_snapshot_executor(self, name, snapshot_executor_generator):
        self.snapshot_executor_map[name] = snapshot_executor_generator
    
    def check_snapshot_executor(self, name) :
        return name in self.snapshot_executor_map
    
    def create_snapshot_executor(self, behavior_executor):
        return self.snapshot_executor_map[behavior_executor.get_name()](behavior_executor)

    def load_snapshot(self, name, shotmodel) :
        model_info = loads(shotmodel) #shotmodel : binary data of model info 
        
        if model_info["type"] != ModelType.BEHAVIORAL :
            raise Exception(f"{model_info['name']} is not of BehaviorModel type")
        
        model = model_info["data"]
                    
        if name != None : 
            model.set_name(name)
            
        return model
        

    

