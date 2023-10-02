#!/usr/bin/env python
#
# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

"""
Module to manage structural model and its components
"""

from abc import abstractmethod
from .structural_model import StructuralModel
from .structural_executor import StructuralExecutor
from .definition import *

class StructuralModelExecutor(BehaviorExecutor):
    def __init__(self, itime=Infinite, dtime=Infinite, ename="default", structural_model = None):
        super().__init__(instantiate_time, destruct_time, engine_name, structural_model)
        
    def ext_trans(self, port, msg):
        super().ext_trans(port, msg)

    # Internal Transition
    def int_trans(self):
        super().int_trans()
        pass

    # Output Function
    def output(self):
        return super().output()

    # Time Advanced Function
    def time_advance(self):
        return super().time_advance()