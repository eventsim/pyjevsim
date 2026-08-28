"""Future-event queue grouped by scheduled time.

A min-heap stores distinct timestamps, and a dictionary maps each timestamp
to its scheduled executors. A reverse map moves or removes an executor when
its request time changes. Empty timestamp entries are discarded when they
reach the head of the heap.
"""

import heapq
from typing import Optional


class ScheduleQueue:
    """Heapset-backed priority queue for executor scheduling."""

    def __init__(self):
        # Empty timestamp buckets are removed lazily by peek and pop.
        self._heap = []
        self._mapped: dict = {}        # time -> set(executor)
        self._reverse: dict = {}       # obj_id -> current scheduled time

    def push(self, executor):
        """Insert or update an executor at its current ``req_time``.

        If the executor was already scheduled at another time, it is removed
        from that bucket. An empty timestamp may remain in the heap until a
        later ``peek_time`` or ``pop``.

        ``get_req_time`` also clears a ``BehaviorExecutor`` cancellation flag
        and updates its previous-event time. Object IDs are stable and read
        from the cached attribute.
        """
        new_t = executor.get_req_time()
        obj_id = executor._obj_id

        old_t = self._reverse.get(obj_id)
        if old_t is not None and old_t != new_t:
            old_bucket = self._mapped.get(old_t)
            if old_bucket is not None:
                old_bucket.discard(executor)
                # Leave an empty timestamp for lazy heap cleanup.

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
            # Drop an empty timestamp and continue.
            heapq.heappop(self._heap)
            self._mapped.pop(t, None)
        raise IndexError("pop from empty ScheduleQueue")

    def pop_all_at(self, time):
        """Remove and return every executor currently scheduled at exactly
        ``time`` as a list.
        """
        bucket = self._mapped.pop(time, None)
        if not bucket:
            return []
        # Remove the matching heap head now; other stale entries are lazy.
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
