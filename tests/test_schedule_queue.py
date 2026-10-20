"""ScheduleQueue batch paths must match the single-executor calls they replace."""

from pyjevsim.behavior_executor import BehaviorExecutor
from pyjevsim.behavior_model import BehaviorModel
from pyjevsim.definition import Infinite
from pyjevsim.executor import Executor
from pyjevsim.schedule_queue import ScheduleQueue


class Timed(BehaviorModel):
    def __init__(self, name, deadline):
        super().__init__(name)
        self.insert_state("wait", deadline)
        self.init_state("wait")


def _executor(name, deadline, cls=BehaviorExecutor):
    return cls(0, Infinite, "default", Timed(name, deadline), None)


def _state(queue, executors):
    buckets = {t: sorted(e.get_name() for e in b) for t, b in queue._mapped.items() if b}
    reverse = {e.get_name(): queue._reverse.get(e.get_obj_id()) for e in executors}
    return buckets, reverse


def _executor_state(ex):
    bm = ex.behavior_model
    return (ex.request_time, ex._next_event_t, ex._cancel_reschedule_f,
            bm._cancel_reschedule_f, ex.global_time, bm.global_time)


def _build(deadlines):
    executors = [_executor(f"m{i}", d) for i, d in enumerate(deadlines)]
    queue = ScheduleQueue()
    for ex in executors:
        ex.set_req_time(0)
        queue.push(ex)
    return queue, executors


def test_reschedule_all_matches_set_req_time_and_push():
    deadlines = [1, 2, 2, 5, Infinite, 3]
    q_ref, ex_ref = _build(deadlines)
    q_new, ex_new = _build(deadlines)

    # Cover moved, unchanged-time, passive and cancelled executors.
    for executors in (ex_ref, ex_new):
        executors[1].behavior_model.cancel_rescheduling()
        executors[1]._cancel_reschedule_f = True
        executors[4].behavior_model.cancel_rescheduling()
        executors[4]._cancel_reschedule_f = True
        executors[5].behavior_model.update_state("wait", 1)

    for ex in ex_ref[1:]:
        ex.set_req_time(2)
        q_ref.push(ex)
    q_new.reschedule_all(ex_new[1:], 2)

    assert _state(q_ref, ex_ref) == _state(q_new, ex_new)
    assert [_executor_state(e) for e in ex_ref] == [_executor_state(e) for e in ex_new]


def test_reschedule_all_keeps_overridden_set_req_time():
    calls = []

    class Recording(BehaviorExecutor):
        def set_req_time(self, global_time):
            calls.append(global_time)
            super().set_req_time(global_time)

    assert Recording._reschedule is Executor._reschedule

    ex = _executor("r", 4, cls=Recording)
    queue = ScheduleQueue()
    queue.reschedule_all([ex], 3)

    assert calls == [3]
    assert queue.peek_time() == 7


def test_reschedule_all_keeps_set_req_time_inherited_from_mixin():
    calls = []

    class DelayMixin:
        def set_req_time(self, global_time):
            calls.append(global_time)
            super().set_req_time(global_time)
            self.request_time += 1

    class Mixed(DelayMixin, BehaviorExecutor):
        pass

    assert Mixed._reschedule is Executor._reschedule

    ex = _executor("x", 4, cls=Mixed)
    queue = ScheduleQueue()
    queue.reschedule_all([ex], 3)

    assert calls == [3]
    assert queue.peek_time() == 8


def test_plain_subclass_keeps_fused_reschedule():
    class Plain(BehaviorExecutor):
        def output(self, msg_deliver):
            return super().output(msg_deliver)

    assert Plain._reschedule is BehaviorExecutor._reschedule


def test_pop_due_matches_peek_and_pop_all_at_loop():
    q_ref, ex_ref = _build([1, 1, 2, 3, 5])
    q_new, ex_new = _build([1, 1, 2, 3, 5])

    expected = []
    while q_ref:
        t = q_ref.peek_time(default=Infinite)
        if t > 3:
            break
        expected.extend(q_ref.pop_all_at(t))

    got = []
    q_new.pop_due(3, got)

    # Same-time order inside a bucket follows set iteration, so compare
    # each timestamp's members and the overall time order.
    assert [e.request_time for e in got] == [e.request_time for e in expected]
    assert sorted(e.get_name() for e in got) == sorted(e.get_name() for e in expected)
    assert _state(q_ref, ex_ref) == _state(q_new, ex_new)
    assert q_new.peek_time() == 5
