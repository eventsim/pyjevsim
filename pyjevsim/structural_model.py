"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains a StructuralModel object that allows you to implement the Discrete Event System Specification CoupledModel. 
"""

from .core_model import CoreModel
from .definition import ModelType
from .system_message import SysMessage

class StructuralModel(CoreModel):
    def __init__(self, _name=""):
        super().__init__(_name, ModelType.STRUCTURAL)

        self.model_map = {}#(name, model)

        self.port_map = {}

    def register_entity(self, obj):
        self.model_map[obj.get_name()] = obj
        
    def remove_model(self, obj) :
        del self.model_map[obj.get_name()]
        
    def find_model(self, name) :
        return self.model_map[name]

    def get_models(self):
        return self.model_map

    def coupling_relation(self, src_obj, src_port, dst_obj, dst_port):
        src = (src_obj, src_port)
        dst = (dst_obj, dst_port)

        # If the source is not in the map, initialize it with an empty list
        if src not in self.port_map:
            self.port_map[src] = []

        # Add the destination to the source's list of destinations
        self.port_map[src].append(dst)
        pass
    
    def get_couplings(self) : 
        return self.port_map