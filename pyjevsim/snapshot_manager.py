from abc import abstractmethod

class SnapshotManager :
    def __init__(self) :
        pass
    
    @abstractmethod
    def get_condition(self, name) :
        if name == "" :
            return self.snapshot_condition
    
    @abstractmethod
    def snapshot_condition(dump_info) : 
        return True
        
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