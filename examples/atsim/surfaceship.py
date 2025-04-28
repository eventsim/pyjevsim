import project_config

from pyjevsim import StructuralModel, Infinite
from manuever import Manuever

class SurfaceShip(StructuralModel):
    def __init__(self, name, manuever_object):
        StructuralModel.__init__(self, name)
        
        self.mo = manuever_object

        man = Manuever(name, manuever_object)

        self.register_entity(man)
        self.insert_input_port("start")
        self.coupling_relation(self, "start", man, "start")

    def get_position(self):
        return self.mo.get_position()