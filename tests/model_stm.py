from pyjevsim.structural_model import StructuralModel

from .model_peg import PEG
from .model_buffer import Buffer

class STM(StructuralModel):
    def __init__(self, name):
        StructuralModel.__init__(self, name)

        self.insert_input_port("start")
        self.insert_output_port("output")
        
        # Model Creation
        peg = PEG("GEN")
        proc = Buffer("Buf")

        # Register Model to StructuralModel
        self.register_entity(peg)        
        self.register_entity(proc)
        
        # Set up relation among models
        self.coupling_relation(self, "start", peg, "start")
        self.coupling_relation(peg, "process", proc, "recv")
        self.coupling_relation(proc, "output", self, "output")