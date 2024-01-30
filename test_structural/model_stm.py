from pyjevsim.structural_model import StructuralModel

from .model_peg import PEG
from .model_buffer import Buffer

class STM(StructuralModel):
    def __init__(self, name):
        StructuralModel.__init__(self, name)

        self.insert_input_port("start")
        self.insert_output_port("output1")
        self.insert_output_port("output2")
        self.insert_output_port("output3")
        
        peg = PEG("GEN")
        self.register_entity(peg)
        proc1 = Buffer("Buf1")
        self.register_entity(proc1)
        
        proc2 = Buffer("Buf2")
        self.register_entity(proc2)
        
        proc3 = Buffer("Buf3")
        self.register_entity(proc3)
        
        proc4 = Buffer("Buf4")
        self.register_entity(proc4)

        self.coupling_relation(self, "start", peg, "start")
        self.coupling_relation(peg, "process1", proc1, "recv")
        self.coupling_relation(peg, "process2", proc2, "recv")
        self.coupling_relation(peg, "process3", proc3, "recv")
        self.coupling_relation(proc1, "output", proc4, "recv")
        self.coupling_relation(proc4, "output", self, "output1")
        self.coupling_relation(proc2, "output", self, "output2")
        self.coupling_relation(proc3, "output", self, "output3")
        
        print(self.port_map)