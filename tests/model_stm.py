from pyjevsim.structural_model import StructuralModel

from .model_peg import PEG
from .model_buffer import Buffer

class STM(StructuralModel):
    def __init__(self, name):
        StructuralModel.__init__(self, name)

        self.insert_input_port("start")
        self.insert_output_port("output")
        peg = PEG("GEN")
        self.register_entity(peg)
        proc = Buffer("Buf")
        self.register_entity(proc)

        self.coupling_relation(self, "start", peg, "start")
        self.coupling_relation(peg, "process", proc, "recv")
        self.coupling_relation(proc, "output", self, "output")
