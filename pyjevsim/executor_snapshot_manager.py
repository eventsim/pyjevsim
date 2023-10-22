from abc import abstractmethod
from dill import loads, dumps
from .definition import ModelType

class ExecutorSnapshotManager :
    def __init__(self) :
        pass
    
    def snapshot_executor(self, engine) : 
        return dumps(engine.model_snapshot())
    
    def load_snapshot(self, shotengine) :
        engine_info = loads(shotengine)
        
        if engine_info["type"] != ModelType.UTILITY:
            raise Exception(f"{engine_info['name']} is not of SystemExecutor type")
        
        engine = engine_info["data"]        
                
        return engine
    
    def cleansing(self, model) :
        return model.get_behavior_executor()    
