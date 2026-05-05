"""Future-event-list priority queue for executor scheduling.

The implementation is a **heapset** — a heap of *unique timestamps* combined
with a ``dict[time → set(executor)]`` mapping. This is the same structure
PythonPDEVS uses in its ``SchedulerHS`` and the structure that wins on
dense DEVS workloads where many models fire at the same simulated instant
(e.g. DEVStone cascades).

Why a heapset rather than a flat lazy heap of ``(time, ..., executor)``
tuples:

  * The heap holds *one* entry per distinct timestamp, not one per
    executor. For DEVStone's collapse-to-t=0 cascade the heap is size 1
    — every imminent model lives in the same bucket.
  * Reschedule is amortised O(1) when the new timestamp is already in
    the heap (just dict-bucket move; no ``heappush``). The ``heappush``
    only fires when a brand-new timestamp appears.
  * No ``heapify`` ever runs.

The class deliberately keeps the same ``push / pop / peek_time / remove``
public API as the previous lazy-heap implementation so call sites in
``SysExecutor`` and ``StructuralExecutor`` do not change.
"""

import heapq
from typing import Optional


class ScheduleQueue:
    """Heapset-backed priority queue for executor scheduling."""

    def __init__(self):
        # Min-heap of unique timestamps that *might* still be live.
        # An entry is "live" iff `_mapped[t]` exists and is non-empty.
        # Empty/absent buckets are cleaned lazily on peek/pop.
        self._heap = []
        self._mapped: dict = {}        # time -> set(executor)
        self._reverse: dict = {}       # obj_id -> current scheduled time

    def push(self, executor):
        """Insert or update an executor at its current ``req_time``.

        If the executor was already in the queue at a different time, that
        old entry is removed from its bucket (lazily — the timestamp may
        stay in the heap until the bucket empties and is pruned by a
        future ``peek_time`` / ``pop``).

        ``get_req_time()`` is intentionally still a method call: on
        ``BehaviorExecutor`` it has the side effect of clearing the
        cancel-reschedule flag and snapshotting ``_next_event_t``. The
        obj-id, however, is stable for the executor's lifetime, so we
        read the cached ``_obj_id`` attribute directly.
        """
        new_t = executor.get_req_time()
        obj_id = executor._obj_id

        old_t = self._reverse.get(obj_id)
        if old_t is not None and old_t != new_t:
            old_bucket = self._mapped.get(old_t)
            if old_bucket is not None:
                old_bucket.discard(executor)
                # Don't bother shrinking the heap here; the empty bucket
                # gets pruned the next time it surfaces at heap[0].

        self._reverse[obj_id] = new_t

        bucket = self._mapped.get(new_t)
        if bucket is None:
            self._mapped[new_t] = {executor}
            heapq.heappush(self._heap, new_t)
        else:
            bucket.add(executor)

    def pop(self):
        """Remove and return one executor with the smallest ``req_time``.

        When multiple executors share the smallest timestamp the choice
        between them is arbitrary (set ordering). Callers that need
        deterministic ordering should use ``pop_all_at(time)`` and sort.
        """
        while self._heap:
            t = self._heap[0]
            bucket = self._mapped.get(t)
            if bucket:
                executor = bucket.pop()
                if not bucket:
                    self._mapped.pop(t, None)
                    heapq.heappop(self._heap)
                obj_id = executor.get_obj_id()
                if self._reverse.get(obj_id) == t:
                    del self._reverse[obj_id]
                return executor
            # Empty / stale bucket — drop and look at the next time.
            heapq.heappop(self._heap)
            self._mapped.pop(t, None)
        raise IndexError("pop from empty ScheduleQueue")

    def pop_all_at(self, time):
        """Remove and return every executor currently scheduled at exactly
        ``time`` as a list. Cheaper than calling ``pop()`` repeatedly when
        many executors share the same timestamp (the common DEVStone case
        — a whole cascade lives at t=0).
        """
        bucket = self._mapped.pop(time, None)
        if not bucket:
            return []
        # Eager cleanup of the heap entry — it will fall to heap[0]
        # eventually and be skipped by peek/pop, but popping it now keeps
        # the heap small under high-churn workloads.
        if self._heap and self._heap[0] == time:
            heapq.heappop(self._heap)
        for executor in bucket:
            obj_id = executor.get_obj_id()
            if self._reverse.get(obj_id) == time:
                del self._reverse[obj_id]
        return list(bucket)

    def peek_time(self, default: Optional[float] = None):
        """Return the smallest non-empty scheduled time without modifying
        which executors are queued at it. Stale heap entries (timestamps
        whose bucket is empty) are pruned eagerly here.
        """
        while self._heap:
            t = self._heap[0]
            bucket = self._mapped.get(t)
            if bucket:
                return t
            heapq.heappop(self._heap)
            self._mapped.pop(t, None)
        if default is not None:
            return default
        raise IndexError("peek from empty ScheduleQueue")

    def remove(self, executor):
        """Remove ``executor`` from the queue if present."""
        obj_id = executor.get_obj_id()
        old_t = self._reverse.pop(obj_id, None)
        if old_t is not None:
            bucket = self._mapped.get(old_t)
            if bucket is not None:
                bucket.discard(executor)
                if not bucket:
                    self._mapped.pop(old_t, None)
                    # Heap entry is left for lazy cleanup.

    def __len__(self):
        return len(self._reverse)

    def __bool__(self):
        return bool(self._reverse)
