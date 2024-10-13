"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Structural Model
"""

from pyjevsim.structural_model import StructuralModel

from .model_peg import PEG
from .model_buffer import Buffer

class STM(StructuralModel):
    def __init__(self, name):
        StructuralModel.__init__(self, name)

        self.insert_input_port("start")
        self.insert_output_port("output")
        
        # Model Creation
        peg = PEG("GEN") #PEG Model(Behavior Model type)
        proc = Buffer("Buf") #Buffer Model(Behavior Model type)

        # Register Model to StructuralModel
        self.register_entity(peg)        
        self.register_entity(proc)
        
        # Set up relation among models
        self.coupling_relation(self, "start", peg, "start")
        self.coupling_relation(peg, "process", proc, "recv")
        self.coupling_relation(proc, "output", self, "output")