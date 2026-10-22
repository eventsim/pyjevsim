"""Object IDs after restoring a snapshot.

Restored models keep the IDs they had in the process that took the
snapshot. In a fresh process the ID counter used to start from zero again,
so the restoring engine's own DefaultMessageCatcher and any model created
afterwards could take a restored model's ID; SysExecutor keys its active
models by ID, so one of the two executors was silently dropped.
"""

import copy
import json
import os
import subprocess
import sys
import textwrap

import pytest

from pyjevsim import system_object
from pyjevsim.definition import ExecutionType
from pyjevsim.restore_handler import RestoreHandler
from pyjevsim.snapshot_manager import SnapshotManager
from pyjevsim.system_executor import SysExecutor
from pyjevsim.system_message import SysMessage
from pyjevsim.system_object import SystemObject

from .model_msg_recv import MsgRecv
from .model_peg import PEG

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_TAKE = textwrap.dedent("""
    import sys
    sys.path.insert(0, {repo!r})
    from pyjevsim.definition import ExecutionType
    from pyjevsim.snapshot_manager import SnapshotManager
    from pyjevsim.system_executor import SysExecutor
    from tests.model_msg_recv import MsgRecv
    from tests.model_peg import PEG

    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=SnapshotManager())
    se.insert_input_port("start")
    gen, proc = PEG("Gen"), MsgRecv("Proc")
    se.register_entity(gen)
    se.register_entity(proc)
    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(gen, "process", proc, "recv")
    se.insert_external_event("start", None)
    for _ in range(20):
        se.simulate(1, _tm=False)
    se.snapshot_simulation(name="ids", directory_path={directory!r})
""")

_RESTORE = textwrap.dedent("""
    import json
    import sys
    sys.path.insert(0, {repo!r})
    from pyjevsim.definition import ExecutionType
    from pyjevsim.restore_handler import RestoreHandler
    from pyjevsim.system_message import SysMessage
    from tests.model_peg import PEG

    rh = RestoreHandler(1, ExecutionType.V_TIME, "ids", path={directory!r})
    se = rh.get_engine()
    new = [PEG("New%d" % i) for i in range(3)]
    for model in new:
        se.register_entity(model)
    for _ in range(3):
        se.simulate(1, _tm=False)
    print(json.dumps({{
        "restored": {{name: m.get_obj_id() for name, m in rh.model_map.items()}},
        "dmc": se.dmc.get_obj_id(),
        "new": [m.get_obj_id() for m in new],
        "message": SysMessage().get_obj_id(),
        "active": len(se.active_obj_map),
    }}))
""")


def _python(template, directory):
    out = subprocess.run(
        [sys.executable, "-c", template.format(repo=REPO, directory=str(directory))],
        capture_output=True, text=True, check=True,
    ).stdout
    return out.strip().splitlines()[-1] if out.strip() else ""


def _manifest(directory):
    with open(os.path.join(directory, "ids", "model_map.json")) as f:
        return json.load(f)


def _check_restored_ids(result):
    restored = list(result["restored"].values())
    ids = restored + [result["dmc"]] + result["new"]
    assert len(set(ids)) == len(ids), result
    # Every restored model, the engine's catcher and the new models are
    # active: none was dropped by an ID collision.
    assert result["active"] == len(ids)
    return max(restored)


def test_peek_does_not_consume_and_reserve_never_moves_back():
    nxt = system_object.peek_next_object_id()
    assert system_object.peek_next_object_id() == nxt
    assert SystemObject().get_obj_id() == nxt

    system_object.reserve_object_ids(nxt + 1000)
    assert SystemObject().get_obj_id() == nxt + 1000
    assert SysMessage().get_obj_id() == nxt + 1001

    system_object.reserve_object_ids(5)
    assert SystemObject().get_obj_id() == nxt + 1002


def test_snapshot_records_next_object_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=SnapshotManager())
    gen = PEG("Gen")
    se.register_entity(gen)
    se.snapshot_simulation(name="ids", directory_path=str(tmp_path))

    recorded = _manifest(tmp_path)["next_object_id"]
    assert gen.get_obj_id() < recorded <= system_object.peek_next_object_id()


def test_restore_in_same_process_gives_new_models_unique_ids(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=SnapshotManager())
    se.insert_input_port("start")
    gen, proc = PEG("Gen"), MsgRecv("Proc")
    se.register_entity(gen)
    se.register_entity(proc)
    se.coupling_relation(se, "start", gen, "start")
    se.coupling_relation(gen, "process", proc, "recv")
    se.insert_external_event("start", None)
    for _ in range(5):
        se.simulate(1, _tm=False)
    se.snapshot_simulation(name="ids", directory_path=str(tmp_path))

    rh = RestoreHandler(1, ExecutionType.V_TIME, "ids", path=str(tmp_path))
    restored = rh.get_engine()
    new = [PEG("New%d" % i) for i in range(3)]
    for model in new:
        restored.register_entity(model)
    restored.simulate(3, _tm=False)

    _check_restored_ids({
        "restored": {n: m.get_obj_id() for n, m in rh.model_map.items()},
        "dmc": restored.dmc.get_obj_id(),
        "new": [m.get_obj_id() for m in new],
        "active": len(restored.active_obj_map),
    })
    assert min(m.get_obj_id() for m in new) >= _manifest(tmp_path)["next_object_id"]


def test_restore_in_fresh_process_gives_new_objects_unique_ids(tmp_path):
    _python(_TAKE, tmp_path)
    recorded = _manifest(tmp_path)["next_object_id"]

    result = json.loads(_python(_RESTORE, tmp_path))

    _check_restored_ids(result)
    # The saved counter covers the messages created before the snapshot,
    # not only the models.
    assert recorded > max(result["restored"].values()) + 1
    assert result["dmc"] >= recorded
    assert min(result["new"]) >= recorded
    assert result["message"] >= recorded


def test_restore_snapshot_without_saved_counter(tmp_path):
    _python(_TAKE, tmp_path)
    path = os.path.join(tmp_path, "ids", "model_map.json")
    manifest = _manifest(tmp_path)
    del manifest["next_object_id"]
    with open(path, "w") as f:
        json.dump(manifest, f)

    result = json.loads(_python(_RESTORE, tmp_path))

    highest = _check_restored_ids(result)
    assert result["dmc"] > highest
    assert min(result["new"]) > highest


def test_register_entity_rejects_duplicate_obj_id():
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    gen = PEG("Gen")
    se.register_entity(gen)

    # Waiting for creation.
    with pytest.raises(ValueError, match="object ID %d" % gen.get_obj_id()):
        se.register_entity(gen)

    # Active.
    se.create_entity()
    twin = copy.deepcopy(gen)
    twin.set_name("Twin")
    with pytest.raises(ValueError, match="'Twin'"):
        se.register_entity(twin)
    assert len(se.get_entity("Gen")) == 1
    assert se.get_entity("Twin") == []

    # A destroyed model's ID is free again.
    se.remove_entity("Gen")
    se.register_entity(twin)


def test_load_snapshot_twice_gives_two_registrable_models(tmp_path, monkeypatch):
    import dill

    gen = PEG("Gen")
    shot = dill.dumps(gen.model_snapshot())
    sm = SnapshotManager(RestoreHandler(path=str(tmp_path)))

    first = sm.load_snapshot("gen0", shot)
    second = sm.load_snapshot("gen1", shot)

    ids = {gen.get_obj_id(), first.get_obj_id(), second.get_obj_id()}
    assert len(ids) == 3
    se = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    se.register_entity(first)
    se.register_entity(second)
    se.create_entity()
    assert {first.get_obj_id(), second.get_obj_id()} <= set(se.active_obj_map)
