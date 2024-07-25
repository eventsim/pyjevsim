"""
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""

from .system_object import SystemObject

class SysMessage(SystemObject):
    """SysMessage for handling messages(port and data) between Models."""

    def __init__(self, src_name="", dst_name=""):
        """
        Args:
            src_name (str): The source name(Model name)
            dst_name (str): The destination name(port)
        """
        super().__init__()
        self._src = src_name  # Source name(Model)
        self._dst = dst_name  # Destination name(port)
        self._msg_time = -1  # Message time
        self._msg_list = []  # List of messages

    def __str__(self):
        """
        Returns the string representation of the message.
        
        Returns:
            str: The string representation
        """
        return super().__str__() + f"\tSRC:{self._src}\t DST:{self._dst}"

    def insert(self, msg):
        """
        Inserts a message into the message list(data).
        
        Args:
            msg (any): The message to insert
        """
        self._msg_list.append(msg)

    def extend(self, _list):
        """
        Extends the message list with multiple messages.
        
        Args:
            _list (list): The list of messages to add
        """
        self._msg_list.extend(_list)

    def retrieve(self):
        """
        Retrieves the list of messages.
        
        Returns:
            list: The list of messages
        """
        return self._msg_list

    def get_src(self):
        """
        Returns the source(model) name of the message.
        
        Returns:
            str: The source name
        """
        return self._src

    def get_dst(self):
        """
        Returns the destination(port) name of the message.
        
        Returns:
            str: The destination(port) name
        """
        return self._dst

    def set_msg_time(self, _time):
        """
        Sets the message time.

        Args:
            _time (float): The time to set
        """
        self._msg_time = _time

    def get_msg_time(self):
        """
        Returns the message time.

        Returns:
            float: The message time 
        """
        return self._msg_time
    