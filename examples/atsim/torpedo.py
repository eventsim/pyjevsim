import project_config

from pyjevsim import StructuralModel, Infinite
from manuever import Manuever
from manuever_object import ManueverObject
from object_db import ObjectDB

class Torpedo(StructuralModel):
    def __init__(self, name, yaml_data):
        StructuralModel.__init__(self, name)
        
        self.mo = ManueverObject(**yaml_data["ManueverObject"])
        ObjectDB().items.append(self.mo)
        man = Manuever(name, self)

        self.register_entity(man)
        self.insert_input_port("start")
        self.coupling_relation(self, "start", man, "start")

    def get_position(self):
        return self.mo.get_position()