import project_config

from pyjevsim import StructuralModel, Infinite
from manuever import Manuever
from detector import Detector
from manuever_object import ManueverObject
from detector_object import DetectorObject
from object_db import ObjectDB

class SurfaceShip(StructuralModel):
    def __init__(self, name, yaml_data):
        StructuralModel.__init__(self, name)
        
        self.mo = ManueverObject(**yaml_data["ManueverObject"])
        ObjectDB().items.append(self.mo)
        self.do = DetectorObject(**yaml_data["DetectorObject"])

        man = Manuever(f"[{name}][Manuever]", self)
        detect = Detector(f"[{name}][Detector]", self)

        self.register_entity(man)
        self.register_entity(detect)

        self.insert_input_port("start")
        self.coupling_relation(self, "start", man, "start")
        self.coupling_relation(self, "start", detect, "start")

    def get_position(self):
        return self.mo.get_position()