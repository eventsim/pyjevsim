"""
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""

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
