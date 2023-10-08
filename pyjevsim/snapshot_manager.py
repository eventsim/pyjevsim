from dill import loads
from .behavior_model import BehaviorModel

class SnapshotManager :
    def __init__(self, snapshot_condition) :
        self.SYSTEM_VERSION = ["1.0"]

        self.snapshot_condition = snapshot_condition
        pass
        
    def get_snapshot_model_name(self, global_time) :
        model_name = self.snapshot_condition(global_time) 
        return model_name
    
    def model_dump(self, model_executor) :
        return model_executor.get_core_model().model_snapshot()
                
    def model_load(self, shotmodel, name = None) :
        model_info = loads(shotmodel) #shotmodel : binary data of model info 
    
        if model_info["version"] not in self.SYSTEM_VERSION :
            raise Exception(f"{model_info['model_name']} model type does not match pyjevsim version")
        
        model = model_info["model_data"]
        
        if  not isinstance(model, BehaviorModel) :
            raise Exception(f"{model_info['model_name']} is not of BehaviorModel type")
            
        if name != None : 
            model.set_name(name)
        
        return model    