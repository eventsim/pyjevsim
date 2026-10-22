"""W1, W2, W7: flattened DEVStone (``benchmark.engines.pyjevsim``).

``events`` seed events are injected at t = 0, P, 2P, ... (the multi-event
mode of ``run_compare``); every zero-delay cascade drains before the next
seed, so the transition count is exact and is the parity key.
"""

import time


def _count(atomics):
    return {
        "atomics": len(atomics),
        "internals": sum(a._n_internals for a in atomics),
        "externals": sum(a._n_externals for a in atomics),
        "events": sum(a._n_events for a in atomics),
    }


def _run(params, snapshot_manager=None, snapshot_condition=None):
    from benchmark.engines.pyjevsim.topology import build, simulate

    variant = params["variant"]
    depth, width = int(params["depth"]), int(params["width"])
    events, period = int(params["events"]), float(params["period"])

    t0 = time.perf_counter()
    ss, atomics, _levels = build(
        variant, depth, width, events=events, period=period,
        snapshot_manager=snapshot_manager,
        snapshot_condition=snapshot_condition)
    t1 = time.perf_counter()
    simulate(ss, depth, width, events=events, period=period)
    t2 = time.perf_counter()

    parity = _count(atomics)
    parity["transitions"] = parity["internals"] + parity["externals"]
    return ss, {
        "metrics": {"sim_s": t2 - t1},
        "build_s": t1 - t0,
        "parity": parity,
        "info": {"transitions_per_s": parity["transitions"] / (t2 - t1)},
    }


def run_devstone(params):
    _ss, result = _run(params)
    return result


def _never_condition():
    from pyjevsim.snapshot_condition import SnapshotCondition

    class NeverSnapshot(SnapshotCondition):
        """A condition that never fires: measures the wrapper cost only."""

        def snapshot_time_condition(self, global_time):
            return False

        def snapshot_pre_condition_ext(self, port, msg, cur_state):
            return False

        def snapshot_post_condition_ext(self, port, msg, cur_state):
            return False

        def snapshot_pre_condition_int(self, cur_state):
            return False

        def snapshot_post_condition_int(self, cur_state):
            return False

        def snapshot_pre_condition_out(self, cur_state):
            return False

        def snapshot_post_condition_out(self, msg, cur_state):
            return False

    return NeverSnapshot


def snapshot_manager():
    """A SnapshotManager whose factory wraps every registered model.

    Snapshot decoration is enabled the way the examples do it
    (``examples/banksim/banksim_model_snapshot.py``): pass a
    ``SnapshotManager`` to ``SysExecutor`` and register a condition per
    model name before ``register_entity``; ``SnapshotFactory`` then wraps the
    model's ``BehaviorExecutor`` in a ``SnapshotExecutor``.

    Returns ``(manager, shimmed)``.  ``SnapshotExecutor`` has no
    ``con_trans`` up to at least 2.2.x (roadmap CORE-5), and the HI chain
    makes models confluent, so on such checkouts the manager's factory
    builds a subclass whose ``con_trans`` forwards to the wrapped
    ``BehaviorExecutor`` (the same shape as its ``ext_trans``/``int_trans``
    without condition checks).  ``shimmed`` is reported in ``info``.
    """
    from pyjevsim.snapshot_executor import SnapshotExecutor
    from pyjevsim.snapshot_factory import SnapshotFactory
    from pyjevsim.snapshot_manager import SnapshotManager

    manager = SnapshotManager()
    if hasattr(SnapshotExecutor, "con_trans"):
        return manager, False

    class ConfluentSnapshotExecutor(SnapshotExecutor):
        def con_trans(self, port_msgs):
            self.behavior_executor.con_trans(port_msgs)

    class ConfluentSnapshotFactory(SnapshotFactory):
        def create_snapshot_executor(self, model):
            cond = self.snapshot_condition_map.get(model.get_name())
            if cond is None:
                return model
            return ConfluentSnapshotExecutor(model, cond(model), model.parent)

    manager.get_snapshot_factory = (
        lambda: ConfluentSnapshotFactory(manager.snapshot_condition_map))
    return manager, True


def run_devstone_snapshot(params):
    from pyjevsim.snapshot_executor import SnapshotExecutor

    manager, shimmed = snapshot_manager()
    ss, result = _run(params, snapshot_manager=manager,
                      snapshot_condition=_never_condition())
    wrapped = sum(isinstance(e, SnapshotExecutor)
                  for e in ss.active_obj_map.values())
    # The parity key holds the outcome only; the wrapped-executor count is
    # a sanity check that decoration really happened.
    if wrapped < result["parity"]["atomics"]:
        raise RuntimeError(
            f"only {wrapped} executors are SnapshotExecutor instances")
    result["info"].update({"snapshot_executors": wrapped,
                           "con_trans_shim": shimmed})
    return result
