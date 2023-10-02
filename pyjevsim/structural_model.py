# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from .core_model import CoreModel
from .definition import ModelType

class StructuralModel(CoreModel):
    def __init__(self, _name=""):
        super().__init__(_name, ModelType.STRUCTURAL)

        self._models = []

        self.external_input_coupling_map = {}
        self.external_output_coupling_map = {}
        self.internal_coupling_map = {}

        self.port_map = {}

    def register_entity(self, _obj):
        self._models.append(_obj)
    
    def get_models(self):
        return self._models

    def coupling_relation(self, src_obj, src_port, dst_obj, dst_port):
        if src_obj == self:
            if (self, src_port) not in self.external_input_coupling_map:
                self.port_map[(self, src_port)] = [(dst_obj, dst_port)]
            else:
                self.port_map[(self, src_port)].append((dst_obj, dst_port))
        elif dst_obj == self:
            self.port_map[(src_obj, src_port)] = (self, dst_port)
        else:# TODO: check redundant port pairs.
            if (src_obj, src_port) not in self.internal_coupling_map:
                self.port_map[(src_obj, src_port)] = [(dst_obj, dst_port)]
            else:
                self.port_map[(src_obj, src_port)].append((dst_obj, dst_port))