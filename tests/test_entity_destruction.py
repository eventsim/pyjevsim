"""Correctness tests for time-based entity destruction.

`SysExecutor.register_entity(..., dest_t=...)` schedules a model for
destruction at an absolute simulated time. The destruction itself is
driven by `destroy_active_entity()`, which:

  * short-circuits unless `_destructs_pending > 0` (the count of active
    executors registered with a finite `dest_t`), and
  * removes every active executor whose cached absolute destruct time
    (`_cached_destruct_time`, exposed via `get_destruct_time()`) has
    reached the current `global_time`.

These tests pin that behaviour down: entities must disappear from
`active_obj_map` at the correct simulated time and in destruct-time
order. This coverage previously lived only in the repo-root
`test_correctness.py` (which is outside `testpaths`); it is migrated
here so the official suite exercises it.
"""

from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.system_executor import SysExecutor


class IdleModel(BehaviorModel):
    """A model that never schedules an internal event of its own.

    It sits passively in the active map so the only thing that ever
    removes it is the executor's time-based destruction. That keeps the
    test focused on `dest_t` handling rather than transition logic.
    """

    def __init__(self, name):
        super().__init__(name)
        self.insert_state("idle", Infinite)
        self.init_state("idle")

    def ext_trans(self, port, msg):
        pass

    def int_trans(self):
        pass

    def output(self, msg_deliver):
        pass


def _build(destruction_times):
    ss = SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)
    for i, dest_t in enumerate(destruction_times):
        ss.register_entity(IdleModel(f"m{i}"), inst_t=0, dest_t=dest_t,
                           ename=f"m{i}")
    return ss


# active_obj_map always contains the built-in DefaultMessageCatcher, so
# every active count includes a +1 for it.
DMC = 1


def test_pending_destruct_count_tracks_finite_dest_t():
    """`_destructs_pending` counts only entities with a finite dest_t."""
    ss = _build([10, 20, Infinite, 30])
    # Infinite dest_t entities and the DefaultMessageCatcher do not count.
    assert ss._destructs_pending == 3


def test_cached_destruct_time_matches_registration():
    """Each executor caches its absolute destruct time (== dest_t here,
    since the entities are registered at global_time 0)."""
    times = [50, 25, 75, 10]
    ss = _build(times)
    ss.simulate(1, _tm=False)  # activate entities

    cached = sorted(
        agent.get_destruct_time()
        for agent in ss.active_obj_map.values()
        if agent.get_destruct_time() < Infinite
    )
    assert cached == sorted(times)


def test_entities_destroyed_at_correct_time():
    """Entities leave active_obj_map exactly when global_time reaches
    their destruct time, regardless of registration order."""
    times = [50, 25, 75, 10, 100, 5, 30, 60, 15, 40]
    ss = _build(times)

    ss.simulate(1, _tm=False)  # activate all entities
    assert len(ss.active_obj_map) == len(times) + DMC

    # As simulated time passes each threshold, one more entity is gone.
    # The dict count is the number of times strictly greater than the
    # current clock, plus the DefaultMessageCatcher.
    prev = 1
    for check_time in sorted(set(times)):
        ss.simulate(check_time - prev, _tm=False)
        prev = check_time
        still_alive = sum(1 for t in times if t > check_time)
        assert len(ss.active_obj_map) == still_alive + DMC, (
            f"at t={check_time}: expected {still_alive + DMC} active, "
            f"got {len(ss.active_obj_map)}"
        )

    # Past the last destruct time only the DefaultMessageCatcher remains.
    assert len(ss.active_obj_map) == DMC
    assert ss._destructs_pending == 0


def test_no_destruction_when_all_infinite():
    """With no finite dest_t the destruction scan is a no-op and every
    registered entity stays active."""
    ss = _build([Infinite, Infinite])
    assert ss._destructs_pending == 0

    ss.simulate(1000, _tm=False)
    # Both models plus the DefaultMessageCatcher survive.
    assert len(ss.active_obj_map) == 2 + DMC
