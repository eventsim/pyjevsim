from abc import abstractstaticmethod
from dill import loads
from .behavior_model import BehaviorModel

class SnapshotManager :
    def __init__(self) :
        self.snapshot_executor_map = {}
        pass
    
    def register_entity(self, name, snapshot_executor_generator):
        self.snapshot_executor_map[name] = snapshot_executor_generator
    
    def check_snapshot_executor(self, name) :
        return name in self.snapshot_executor_map
    
    def create_snapshot_executor(self, behavior_executor):
        return self.snapshot_executor_map[behavior_executor.get_name()](behavior_executor)
    
    
    def model_load(self, shotmodel, name = None) :
        model_info = loads(shotmodel) #shotmodel : binary data of model info 
    
        model = model_info["model_data"]
        
        if  not isinstance(model, BehaviorModel) :
            raise Exception(f"{model_info['model_name']} is not of BehaviorModel type")
            
        if name != None : 
            model.set_name(name)
        
        return model    
    