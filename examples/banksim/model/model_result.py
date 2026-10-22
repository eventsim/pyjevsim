"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains Banksim User Generator Model 
"""
import os
import sys
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import *

class BankResult(BehaviorModel):
    """A Model representing a bank user generator."""

    def __init__(self, name, max_user):
        """
        Args:
            name (str): Name of Model
            cycle (float): Generation cycle time
            max_user (int): Maximum number of users to generate
            proc_time (float): Processing time for each user
        """
        BehaviorModel.__init__(self, name)
        self.init_state("WAIT")  # Initialize initial state
        self.insert_state("WAIT", Infinite)  # Add "WAIT" state
        
        self.insert_input_port("process")  # Add input port "process"
        self.insert_input_port("drop")  # Add input port "drop"

        self.max_user = max_user  # Maximum number of users to generate
        self.user_count = 0
        self.user = []
        self.drop_user = []
        self.drop_user_count = 0
        
    def ext_trans(self, port, msg):
        """
        Handles external transitions based on the input port.

        Args:
            port (str): The port that received the message
            msg (SysMessage): The received message
        """
        if port == "process":
            proc = msg.retrieve()[0]
            _user = msg.retrieve()[1]
                
            self.user.append((proc, _user))
            self.user_count += 1
            if self.user_count >= self.max_user :
                self.get_result()
                os._exit(0)
                
        if port == "drop" :
            drop_user_list = msg.retrieve()[0]
            for _user in drop_user_list : 
                self.drop_user.append(_user)
                self.drop_user_count += 1

    def output(self, msg_deliver):
        pass

    def int_trans(self):
        pass
        
    def get_result(self) :
        """Write the end-of-run report to ``sys.stdout`` and flush it once.

        The text is the same as one ``print`` per line, but it is written in
        large chunks instead of being flushed line by line (500000 users make
        a report of about a million lines).  The single flush at the end
        matters: ``ext_trans`` calls ``os._exit(0)`` right after this method,
        and ``os._exit`` does not flush Python's buffers.
        """
        out = sys.stdout
        lines = [
            "[BANKSIM RESULT]\n",
            "- Accountant user :  %s\n" % (self.user_count,),
            "- Dropped user :  %s\n" % (self.drop_user_count,),
            "\n [Accountant user list]\n",
        ]
        chunk = 65536
        for p, u in self.user :
            lines.append("%s %s\n" % (p, u.__str__()))
            if len(lines) >= chunk :
                out.write("".join(lines))
                lines.clear()
        lines.append("\n [Dropped user list]\n")
        for d in self.drop_user :
            lines.append("%s\n" % (d.__str__(),))
            if len(lines) >= chunk :
                out.write("".join(lines))
                lines.clear()
        out.write("".join(lines))
        out.flush()


class OrderedBankResult(BankResult):
    """A :class:`BankResult` whose report does not depend on message order.

    ``BankResult`` records served users in the order in which the engine
    delivers the accountants' messages of an instant, which follows set
    iteration and can change between processes; so can the order of the
    report and which messages of the last instant are counted before the
    run ends at ``max_user``.  This variant collects the messages of an
    instant in ``inbox``, moves to the zero-duration ``SORT`` state and
    applies them in its internal transition with ``BankResult.ext_trans``,
    sorted by port, accountant and user ID.  The seeded ``banksim_*.py``
    runs use it together with
    :class:`~examples.banksim.model.model_queue.OrderedBankQueue`.
    """

    def __init__(self, name, max_user):
        BankResult.__init__(self, name, max_user)
        self.insert_state("SORT", 0)
        self.inbox = []

    def ext_trans(self, port, msg):
        self.inbox.append((port, msg))
        self._cur_state = "SORT"

    def int_trans(self):
        if self._cur_state == "SORT":
            inbox = sorted(self.inbox, key=_result_msg_key)
            self.inbox = []
            self._cur_state = "WAIT"
            for port, msg in inbox:
                BankResult.ext_trans(self, port, msg)


def _result_msg_key(port_msg):
    port, msg = port_msg
    body = msg.retrieve()
    if port == "process":
        return (port, str(body[0]), str(body[1].get_id()))
    return (port, "", ",".join(str(u.get_id()) for u in body[0]))
