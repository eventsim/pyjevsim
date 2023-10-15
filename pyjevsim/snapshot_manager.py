from abc import abstractmethod
from dill import loads
from .definition import ModelType

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
        
        if model_info["type"] != ModelType.BEHAVIORAL :
            raise Exception(f"{model_info['name']} is not of BehaviorModel type")
        
        model = model_info["data"]
                    
        if name != None : 
            model.set_name(name)
        
        return model    
    
    def engine_load(self, shotengine, name = None) : 
        engine_info = loads(shotengine)
        
        if engine_info["type"] != ModelType.UTILITY:
            raise Exception(f"{engine_info['name']} is not of BehaviorModel type")
        
        engine = engine_info["data"]
        
        if name != None : 
            engine.set_name(name)
            
        return engine
    
    @abstractmethod 
    def debug(self, engine, global_time) :
        pass
