import os
import dill
from .definition import ModelType

class DebuggingManager :
    def __init__(self) :
        pass
    
    def dump_simulation(self, engine, global_time, snapshot_cycle, path) :
        if int(global_time) % snapshot_cycle == 0 :
            engine_info = engine.model_snapshot()
            with open(f"{path}.simx", "wb") as f :
                dill.dump(engine_info, f)
    
    def load_last_engine(path) :
        file_list = os.listdir(path)
        return path + file_list[-1]
    
    def engine_load(self, shotengine, name = None) : 
        engine_info = dill.loads(shotengine)
        
        if engine_info["type"] != ModelType.UTILITY:
            raise Exception(f"{engine_info['name']} is not of BehaviorModel type")
        
        engine = engine_info["data"]
        
        if name != None : 
            engine.set_name(name)
            
        return engine