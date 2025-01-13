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

        self.external_input_coupling_map = {}
        self.external_output_coupling_map = {}
        self.internal_coupling_map = {}

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
        return self.internal_coupling_map
    
    """
    def coupling_relation(self, src_obj, src_port, dst_obj, dst_port):
        if src_obj == self:
            if (self, src_port) not in self.external_input_coupling_map:
                self.port_map[(self, src_port)] = [(dst_obj, dst_port)]
            else:
                self.port_map[(self, src_port)].append((dst_obj, dst_port))
        elif dst_obj == self:
            self.port_map[(src_obj, src_port)] = [(self, dst_port)]
            #self.port_map[(src_obj, src_port)] = (self, dst_port)
        else:  # TODO: check redundant port pairs.
            if (src_obj, src_port) not in self.internal_coupling_map:
                self.port_map[(src_obj, src_port)] = [(dst_obj, dst_port)]
            else:
                self.port_map[(src_obj, src_port)].append((dst_obj, dst_port))

    """