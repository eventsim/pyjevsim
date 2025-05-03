import project_config

from pyjevsim import StructuralModel, Infinite

from .tracking_manuever import TrackingManuever as Manuever
from mobject.manuever_object import ManueverObject

from .detector import Detector
from mobject.detector_object import DetectorObject

from .torpedo_controller import TorpedoCommandControl as CommandControl
from mobject.comand_control_object import CommandControlObject

from utils.object_db import ObjectDB

class Torpedo(StructuralModel):
    def __init__(self, name, yaml_data):
        StructuralModel.__init__(self, name)
        
        # Model Object Instantiation        
        self.mo = ManueverObject(**yaml_data["ManueverObject"])
        self.do = DetectorObject(**yaml_data["DetectorObject"])
        self.co = CommandControlObject(**yaml_data["TorpedoControlObject"])
        
        ObjectDB().items.append(self.mo)
        
        # Model Instantiation
        man = Manuever(f"[{name}][Manuever]", self)
        detect = Detector(f"[{name}][Detector]", self)
        command = CommandControl(f"[{name}][ComandControl]", self)

        # Model Registration
        self.register_entity(man)
        self.register_entity(detect)
        self.register_entity(command)

        # Port Registration
        self.insert_input_port("start")

        # Coupling Handling
        self.coupling_relation(self, "start", man, "start")
        self.coupling_relation(self, "start", detect, "start")
        self.coupling_relation(detect, "threat_list", command, "threat_list")
        self.coupling_relation(command, "target", man, "target")

    def get_position(self):
        return self.mo.get_position()