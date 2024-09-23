"""
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2024 Handong Global University
 Copyright (c) 2014-2024 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
""" This module contains SystemObject, the top-level class for all models. """

import datetime

class SystemObject:
    """Base class for all system objects, providing unique object IDs and creation time."""

    # Object ID which tracks the entire instantiated Objects
    __GLOBAL_OBJECT_ID = 0

    def __init__(self):
        self.__created_time = datetime.datetime.now()  # Creation time
        self.__object_id = SystemObject.__GLOBAL_OBJECT_ID  # Unique object ID
        SystemObject.__GLOBAL_OBJECT_ID += 1  # Increment global object ID
        
    def __str__(self):
        """
        Returns the string representation of the SystemObject.

        Returns:
            str: The string representation
        """
        return f"ID:{self.__object_id} {self.__created_time}"

    def __lt__(self, other):
        """
        Compares this object with another object for sorting.

        Args:
            other (SystemObject): The other object to compare with

        Returns:
            bool: True if this object ID is less than the other object's ID
        """
        return self.__object_id < other.__object_id

    def get_obj_id(self):
        """
        Returns the unique object ID.

        Returns:
            int: The unique object ID
        """
        return self.__object_id