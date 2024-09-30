"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
""" This module contains the configuration object StructuralModelExeuctor, which decorates the StructuralExecutor for model compatibility with pyevsim, a Python-based simulation engine.  """

from .definition import Infinite
from .structural_executor import StructuralExecutor


class StructuralModelExecutor(StructuralExecutor):
    def __init__(
        self,
        global_time,
        itime=Infinite,
        dtime=Infinite,
        ename="default",
        structural_model=None,
        creator_f=None,
    ):
        super().__init__(global_time, itime, dtime, ename, structural_model, creator_f)
