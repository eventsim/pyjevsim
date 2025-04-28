from pyjevsim import StructuralModel, Infinite
from manuever import Manuever

class SurfaceShip(StructuralModel):
    def __init__(self, inst, dest, name, engine_name):
        StructuralModel.__init__(self, name)
        man = Manuever(0, Infinite, "Gen", "first")

        self.register_entity(man)
        self.insert_input_port("start")
        self.coupling_relation(self, "start", man, "start")
