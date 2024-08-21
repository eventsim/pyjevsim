"""
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""

from .behavior_executor import BehaviorExecutor
from .definition import Infinite

class BehaviorModelExecutor(BehaviorExecutor):
    """
    Allows the use of models from DEVS Module “pyevsim” via the decorator technique.
    """
    def __init__(
        self, itime=Infinite, dtime=Infinite, ename="default", behavior_model=""
    ):
        """
        Args:
            itime (int or Infinite): Time of instance creation
            dtime (int or Infinite): Time of instance destruction
            ename (str): SysExecutor name
            behavior_model (ModelType.BEHAVIORAL): Behavior Model
        """
        super().__init__(itime, dtime, ename, behavior_model)
