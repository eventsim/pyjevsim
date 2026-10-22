"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

"""
from .definition import ModelType, ExecutionType
from .system_executor import SysExecutor
from .system_object import assign_new_object_id, reserve_object_ids

class RestoreHandler():
    """ Restore a snapshotted model or project.
    """
    def __init__(self, t_resol=1, ex_mode=ExecutionType.V_TIME, name="project", path="./snapshot"):
        """
        Initializes the RestoreHandler with time resolution, execution mode, name, and path.

        Args:
            t_resol (float): Time resolution
            ex_mode (R_TIME or V_TIME): Execution mode(Real time or Virtual time)
            name (str): Name of SysExecutor
            path (str, optional): Path to load snapshots
        """
        self.path = f"{path}/{name}"
        self.sim_name = name
        self.t_resol = t_resol
        self.ex_mode = ex_mode
        # Built by restore_engine, after the object-ID counter has been
        # moved past the restored models: the engine's own
        # DefaultMessageCatcher must not take one of their IDs.
        self.engine = None
        self.model_map = {}
        
    def restore_engine(self):
        """
        Creates a SysExecutor and sets it up with the relation map and model map.

        Objects created after this call get IDs above those of the restored
        objects: above the counter value saved with the snapshot or, for a
        snapshot saved without it, above the highest restored model ID.
        """
        import ast
        import json

        with open(f"{self.path}/relation_map.json", "r") as f:
            relation = json.load(f)   
        relation = {ast.literal_eval(key): ast.literal_eval(value) for key, value in relation.items()}

        model_list = {}
        with open(f"{self.path}/model_map.json", "r") as f:
            model_list = json.load(f)  
        next_object_id = model_list.get("next_object_id", 0)
        model_list = model_list["model_name"]

        self.load_models(model_list, next_object_id)
        self.relations(relation)

    def load_models(self, model_list, next_object_id=0):
        """
        Loads models from files, creates the SysExecutor and registers them with it.
        
        Args:
            model_list (list): List of model names
            next_object_id (int, optional): Object-ID counter value saved
                with the snapshot
        """
        from dill import load

        self.model_map = {}
        for model_name in model_list:
            with open(f"{self.path}/{model_name}.simx", "rb") as f:
                model = load(f)
            self.model_map[model_name] = model["data"]

        reserve_object_ids(max(
            [next_object_id]
            + [model.get_obj_id() + 1 for model in self.model_map.values()]))
        self.engine = SysExecutor(self.t_resol, self.sim_name, self.ex_mode, snapshot_manager=None)
        for model in self.model_map.values():
            self.engine.register_entity(model)

    def relations(self, relation_map):
        """
        Sets up coupling relations in SysExecutor.
        
        Args:
            relation_map (dict): The relation map / 관계 맵
        """
        for key, value in relation_map.items():
            if key[0] in self.model_map.keys():
                output_model = self.model_map[key[0]]
            else:
                output_model = self.engine
            for model in value:
                if model[0]:
                    input_model = self.model_map[model[0]]
                else:
                    input_model = self.engine
                self.engine.coupling_relation(output_model, key[1], input_model, model[1])

    def get_engine(self):
        """Returns the SysExecutor.

        Returns:
            Restored SysExecutor
        """
        self.restore_engine()
        return self.engine
    
    def load_snapshot(self, name, shotmodel):
        """Loads BehaviorModel.

        The model is a new instance and gets a new object ID, so the same
        snapshot can be loaded and registered more than once.
        
        Args:
            name (str): The name of Model
            shotmodel (bytes): Binary data of the model snapshot
        
        Returns:
            object(BehaviorModel): The loaded model
        
        Raises:
            Exception: If the model type is not ModelType.BEHAVIORAL
        """
        from dill import loads

        model_info = loads(shotmodel)
        
        if model_info["type"] != ModelType.BEHAVIORAL and model_info["type"] != ModelType.STRUCTURAL :
            raise Exception(f"{model_info['name']} is not of Model type")
        
        model = model_info["data"]
        assign_new_object_id(model)
                    
        if name is not None:
            model.set_name(name)
            
        return model
