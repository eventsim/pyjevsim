# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from .behavior_model import BehaviorModel
from .system_message import SysMessage
from .definition import *

class DefaultMessageCatcher(BehaviorModel):
    def __init__(self, _name):
        super().__init__(_name)
        
        self.init_state("IDLE")
        self.insert_state("IDLE", Infinite)

        self.insert_input_port("uncaught")
        
    def ext_trans(self, port, msg):
        data = msg.retrieve()

    def int_trans(self):
        return

    def output(self):
        return None