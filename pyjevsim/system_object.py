"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains SystemObject, the top-level class for all models.
"""

import itertools

# Shared source of object IDs. It is advanced, never rebound: rebinding a
# class attribute on every instantiation (the former
# ``SystemObject.__GLOBAL_OBJECT_ID += 1``) invalidates the type version of
# SystemObject and every subclass, and once CPython's per-type cap on version
# reassignments is reached the interpreter stops specialising attribute access
# on all models, executors and messages for the rest of the process.
# SysMessage draws from it directly.
_next_object_id = itertools.count().__next__


class SystemObject:
    """Base class for all system objects, providing unique object IDs.

    Note: an earlier version also stamped a ``datetime.now()`` creation
    time on every object. That field was only ever read by ``__str__``
    and never used elsewhere, but the ``datetime.now()`` call was
    measurable in hot allocation paths (every ``SysMessage`` paid for
    it). It has been removed.
    """

    def __init__(self):
        self.__object_id = _next_object_id()  # Unique object ID

    def __str__(self):
        """
        Returns the string representation of the SystemObject.

        Returns:
            str: The string representation
        """
        return f"ID:{self.__object_id}"

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