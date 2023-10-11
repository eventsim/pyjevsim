from abc import abstractstaticmethod

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
    
    """
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
    """