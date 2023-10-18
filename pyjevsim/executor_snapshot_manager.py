from abc import abstractmethod
from dill import loads
from .definition import ModelType

class EngineSnapshotManager :
    def __init__(self) :
        pass
    
    def snapshot_executor(self, engine) : 
        return engine.model_snapshot()        
    
    def load_snapshot(self, shotengine, model_snapshot_manager) :
        engine_info = loads(shotengine)
        
        if engine_info["type"] != ModelType.UTILITY:
            raise Exception(f"{engine_info['name']} is not of SystemExecutor type")
        
        engine = engine_info["data"]
            
        engine.set_snapshot_manager(model_snapshot_manager)
        
                
        return engine
