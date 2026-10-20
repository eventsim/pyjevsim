"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Regression tests for SystemObject ID allocation.
"""
from pyjevsim.system_object import SystemObject
from pyjevsim.system_message import SysMessage


def test_ids_are_unique_and_increasing():
    objs = [SystemObject() for _ in range(5000)]
    ids = [o.get_obj_id() for o in objs]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)
    assert SysMessage("src", "dst").get_obj_id() > ids[-1]
    assert objs[0] < objs[1]


def test_instantiation_does_not_rebind_class_attributes():
    # Rebinding a class attribute per instance invalidates the type version
    # of SystemObject and all its subclasses, which disables CPython's
    # attribute specialisation once the per-type cap is exhausted.
    before = {k: id(v) for k, v in vars(SystemObject).items()}
    for _ in range(3000):
        SysMessage("src", "dst")
    after = {k: id(v) for k, v in vars(SystemObject).items()}
    assert before == after
