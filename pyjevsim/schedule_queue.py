"""Future-event queue grouped by scheduled time.

A min-heap stores distinct timestamps, and a dictionary maps each timestamp
to its scheduled executors. A reverse map moves or removes an executor when
its request time changes. Empty timestamp entries are discarded when they
reach the head of the heap.
"""

import heapq


# Sentinel that compares unequal to every request time (NaN != NaN).
_NO_TIME = float("nan")


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
        mapped = self._mapped

        old_t = self._reverse.get(obj_id)
        if old_t != new_t:
            if old_t is not None:
                old_bucket = mapped.get(old_t)
                if old_bucket is not None:
                    old_bucket.discard(executor)
                    # Leave an empty timestamp for lazy heap cleanup.
            self._reverse[obj_id] = new_t

        bucket = mapped.get(new_t)
        if bucket is None:
            mapped[new_t] = {executor}
            heapq.heappush(self._heap, new_t)
        else:
            bucket.add(executor)

    def reschedule_all(self, executors, global_time):
        """Recompute each executor's request time and move it in the queue.

        Equivalent to ``executor.set_req_time(global_time)`` followed by
        ``push(executor)`` for each executor in iteration order. The two
        executor calls are fused into ``Executor._reschedule``.
        """
        heap = self._heap
        mapped = self._mapped
        reverse = self._reverse
        # Executors of one instant mostly share a few timestamps (the
        # instant itself, Infinite), so the last bucket looked up on each
        # side is kept: a float comparison replaces the dict lookup. Buckets
        # are only deleted by peek_time/pop/pop_all_at/pop_due, never in
        # this loop, so a cached bucket stays the one mapped at its time.
        add_t = del_t = _NO_TIME
        add_bucket = del_bucket = None
        for executor in executors:
            new_t = executor._reschedule(global_time)
            obj_id = executor._obj_id

            old_t = reverse.get(obj_id)
            if old_t != new_t:
                if old_t is not None:
                    if old_t != del_t:
                        del_t = old_t
                        del_bucket = mapped.get(old_t)
                    if del_bucket is not None:
                        del_bucket.discard(executor)
                reverse[obj_id] = new_t

            if new_t == add_t:
                add_bucket.add(executor)
                continue
            bucket = mapped.get(new_t)
            if bucket is None:
                mapped[new_t] = bucket = {executor}
                heapq.heappush(heap, new_t)
                if new_t == del_t:
                    del_bucket = bucket
            else:
                bucket.add(executor)
            add_t = new_t
            add_bucket = bucket

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
        heap = self._heap
        if heap and heap[0] == time:
            heapq.heappop(heap)
        reverse = self._reverse
        for executor in bucket:
            obj_id = executor._obj_id
            if reverse.get(obj_id) == time:
                del reverse[obj_id]
        return list(bucket)

    def pop_due(self, now, out):
        """Move every executor scheduled at or before ``now`` into ``out``.

        Buckets are taken in time order, each in ``pop_all_at`` order. This
        matches repeating ``peek_time`` and ``pop_all_at`` while the queue is
        non-empty.
        """
        heap = self._heap
        mapped = self._mapped
        reverse = self._reverse
        while reverse and heap:
            t = heap[0]
            bucket = mapped.get(t)
            if not bucket:
                heapq.heappop(heap)
                mapped.pop(t, None)
                continue
            if t > now:
                break
            heapq.heappop(heap)
            del mapped[t]
            # One dict operation in the common case: take the entry and put
            # it back only when it points elsewhere (shared obj_id).
            take = reverse.pop
            for executor in bucket:
                obj_id = executor._obj_id
                rt = take(obj_id, None)
                if rt is not None and rt != t:
                    reverse[obj_id] = rt
            out.extend(bucket)

    def peek_time(self, default: float | None = None):
        """Return the smallest non-empty scheduled time without modifying
        which executors are queued at it. Stale heap entries (timestamps
        whose bucket is empty) are pruned eagerly here.
        """
        heap = self._heap
        mapped = self._mapped
        while heap:
            t = heap[0]
            if mapped.get(t):
                return t
            heapq.heappop(heap)
            mapped.pop(t, None)
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
