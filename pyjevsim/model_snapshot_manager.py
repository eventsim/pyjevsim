from abc import abstractmethod
from dill import loads
from .definition import ModelType

class ModelSnapshotManager :
    def __init__(self) :
        self.snapshot_executor_map = {}
        self.load_snapshot_map = {}
        pass
    
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
            
        self.load_snapshot_map[name] = model
        
    def restore_entity(self, name) :
        return self.load_snapshot_map[name]
    

    
