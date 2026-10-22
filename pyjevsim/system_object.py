"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains SystemObject, the top-level class for all models.
"""

import itertools

# Shared source of object IDs. Creating an object advances it; it is a module
# global, not a class attribute: rebinding a class attribute on every
# instantiation (the former ``SystemObject.__GLOBAL_OBJECT_ID += 1``)
# invalidates the type version of SystemObject and every subclass, and once
# CPython's per-type cap on version reassignments is reached the interpreter
# stops specialising attribute access on all models, executors and messages
# for the rest of the process. SysMessage draws from it directly; only
# reserve_object_ids rebinds it, in both modules.
_next_object_id = itertools.count().__next__


def peek_next_object_id():
    """Return the ID the next object will get, without consuming it."""
    # itertools.count has no accessor for its position; its repr is
    # "count(<next value>)".
    return int(repr(_next_object_id.__self__)[len("count("):-1])


def reserve_object_ids(next_id):
    """Make sure no object created from now on gets an ID below ``next_id``.

    Objects restored from a snapshot keep the IDs they were given in the
    process that took it; reserving past them stops new objects from
    reusing those IDs. The counter never moves backwards.

    Args:
        next_id (int): Lowest ID the next object may get
    """
    global _next_object_id
    if next_id <= peek_next_object_id():
        return
    _next_object_id = itertools.count(next_id).__next__
    # SysMessage bound the counter when it was imported.
    from . import system_message
    system_message._next_object_id = _next_object_id


def assign_new_object_id(obj):
    """Give ``obj`` a fresh ID from the shared counter.

    Args:
        obj (SystemObject): Object to renumber, e.g. a model loaded from a
            snapshot as a new instance
    """
    obj._SystemObject__object_id = _next_object_id()


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