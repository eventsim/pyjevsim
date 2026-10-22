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


def test_reschedule_all_matches_push_over_many_instants():
    # reschedule_all caches the last bucket looked up on each side; drive
    # it through many instants where executors keep moving between a few
    # shared timestamps, popping due buckets in between.
    import random

    rng = random.Random(7)
    choices = [1, 2, 3, Infinite]
    deadlines = [rng.choice(choices) for _ in range(40)]
    q_ref, ex_ref = _build(deadlines)
    q_new, ex_new = _build(deadlines)
    index = {id(e): i for i, e in enumerate(ex_ref + ex_new)}

    for now in range(1, 40):
        due_ref, due_new = [], []
        q_ref.pop_due(now, due_ref)
        q_new.pop_due(now, due_new)
        popped = sorted(index[id(e)] for e in due_ref)
        assert popped == sorted(index[id(e)] - len(ex_ref) for e in due_new)

        chosen = sorted(set(popped) | set(rng.sample(range(40), 8)))
        rng.shuffle(chosen)
        for i in chosen:
            d = rng.choice(choices)
            cancel = rng.random() < 0.2
            for ex in (ex_ref[i], ex_new[i]):
                ex.behavior_model.update_state("wait", d)
                if cancel:
                    ex.behavior_model.cancel_rescheduling()
                    ex._cancel_reschedule_f = True
        for i in chosen:
            ex_ref[i].set_req_time(now)
            q_ref.push(ex_ref[i])
        q_new.reschedule_all([ex_new[i] for i in chosen], now)

        assert _state(q_ref, ex_ref) == _state(q_new, ex_new)
        assert len(q_ref) == len(q_new)
        assert q_ref.peek_time(default=Infinite) == q_new.peek_time(default=Infinite)
    assert [_executor_state(e) for e in ex_ref] == [_executor_state(e) for e in ex_new]


def test_pop_due_keeps_shared_obj_id_scheduled_elsewhere():
    # Two executors sharing an obj_id (a model restored twice): popping
    # the earlier one must leave the reverse entry of the later one, or
    # the queue reports empty and the later executor is never popped.
    import copy

    proto = Timed("p", 1)
    early = BehaviorExecutor(0, Infinite, "default", copy.deepcopy(proto), None)
    late_model = copy.deepcopy(proto)
    late_model.update_state("wait", 5)
    late = BehaviorExecutor(0, Infinite, "default", late_model, None)
    assert early.get_obj_id() == late.get_obj_id()

    for queue_pop in ("pop_due", "pop_all_at"):
        queue = ScheduleQueue()
        for ex in (early, late):
            ex.set_req_time(0)
            queue.push(ex)
        if queue_pop == "pop_due":
            got = []
            queue.pop_due(1, got)
        else:
            got = queue.pop_all_at(1)
        assert got == [early]
        assert len(queue) == 1 and queue
        rest = []
        queue.pop_due(5, rest)
        assert rest == [late]
        assert not queue


def test_pop_due_shared_obj_id_in_one_bucket_leaves_queue_empty():
    # Both executors sharing an obj_id sit in the same bucket: the second
    # one finds the reverse entry already taken, which must stay a no-op
    # (no entry is re-created, so len()/bool() report an empty queue).
    import copy

    proto = Timed("p", 2)
    a = BehaviorExecutor(0, Infinite, "default", copy.deepcopy(proto), None)
    b = BehaviorExecutor(0, Infinite, "default", copy.deepcopy(proto), None)
    assert a.get_obj_id() == b.get_obj_id()

    for queue_pop in ("pop_due", "pop_all_at"):
        queue = ScheduleQueue()
        for ex in (a, b):
            ex.set_req_time(0)
            queue.push(ex)
        if queue_pop == "pop_due":
            got = []
            queue.pop_due(2, got)
        else:
            got = queue.pop_all_at(2)
        assert sorted(map(id, got)) == sorted(map(id, (a, b)))
        assert len(queue) == 0 and not queue
        assert queue._reverse == {}
