import project_config

from pyjevsim import StructuralModel, Infinite

from .manuever import Manuever
from mobject.manuever_object import ManueverObject

from .detector import Detector
from mobject.detector_object import DetectorObject

from .command_control import CommandControl
from mobject.comand_control_object import CommandControlObject

from .launcher import Launcher
from mobject.launcher_object import LauncherObject

from utils.object_db import ObjectDB


class SurfaceShip(StructuralModel):
    def __init__(self, name, yaml_data):
        StructuralModel.__init__(self, name)

        # Model Object Instantiation        
        self.mo = ManueverObject(**yaml_data["ManueverObject"])
        self.do = DetectorObject(**yaml_data["DetectorObject"])
        self.co = CommandControlObject(**yaml_data["CommandControlObject"])
        self.lo = LauncherObject(**yaml_data["LauncherObject"])

        # Utilities Instantiation
        ObjectDB().items.append(self.mo)

        # Model Instantiation
        man = Manuever(f"[{name}][Manuever]", self)
        detect = Detector(f"[{name}][Detector]", self)
        command = CommandControl(f"[{name}][ComandControl]", self)
        launcher = Launcher(f"[{name}][Launcher]", self)

        # Model Registration
        self.register_entity(man)
        self.register_entity(detect)
        self.register_entity(command)
        self.register_entity(launcher)

        # Port Registration
        self.insert_input_port("start")

        # Coupling Handling
        self.coupling_relation(self, "start", man, "start")
        self.coupling_relation(self, "start", detect, "start")
        self.coupling_relation(detect, "threat_list", command, "threat_list")
        self.coupling_relation(command, "launch_order", launcher, "order")

    def get_position(self):
        return self.mo.get_position()