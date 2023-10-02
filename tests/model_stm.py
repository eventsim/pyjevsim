from pyjevsim.structural_model import StructuralModel
from .model_peg import PEG
from .model_msg_recv import MsgRecv

class STM(StructuralModel):
    def __init__(self, name):
        StructuralModel.__init__(self, name)
        
        self.insert_input_port("start")
        peg = PEG("GEN")
        self.register_entity(peg)
        proc = MsgRecv("PROC")
        self.register_entity(proc)

        self.coupling_relation(self, "start", peg, "start")
        self.coupling_relation(peg, "process", proc, "recv")