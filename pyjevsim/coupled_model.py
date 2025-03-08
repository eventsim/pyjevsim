"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains a StructuralModel object that allows you to implement the Discrete Event System Specification CoupledModel. 
"""

from .structural_model import StructuralModel
from .definition import ModelType


class CoupledModel(StructuralModel):
    def __init__(self, _name=""):
        super().__init__(_name)