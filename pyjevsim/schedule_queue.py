"""Utilities for maintaining time-ordered executor schedules."""

import heapq
import itertools
from typing import Optional


class ScheduleQueue:
    """Heap-backed priority queue for executor scheduling."""

    def __init__(self):
        self._heap = []
        self._entries = {}
        self._counter = itertools.count()

    def push(self, executor):
        """Insert or update an executor in the queue."""
        req_time = executor.get_req_time()
        entry_id = next(self._counter)
        entry = (req_time, executor.get_obj_id(), entry_id, executor)
        self._entries[executor.get_obj_id()] = (req_time, entry_id)
        heapq.heappush(self._heap, entry)

    def pop(self):
        """Pop the executor with the lowest request time."""
        while self._heap:
            req_time, obj_id, entry_id, executor = heapq.heappop(self._heap)
            current = self._entries.get(obj_id)
            if current and current == (req_time, entry_id):
                del self._entries[obj_id]
                return executor
        raise IndexError("pop from empty ScheduleQueue")

    def peek_time(self, default: Optional[float] = None):
        """Return the smallest request time without removing entries."""
        while self._heap:
            req_time, obj_id, entry_id, _ = self._heap[0]
            current = self._entries.get(obj_id)
            if current and current == (req_time, entry_id):
                return req_time
            heapq.heappop(self._heap)
        if default is not None:
            return default
        raise IndexError("peek from empty ScheduleQueue")

    def remove(self, executor):
        """Remove an executor from the queue if present."""
        self._entries.pop(executor.get_obj_id(), None)

    def __len__(self):
        return len(self._entries)

    def __bool__(self):
        return bool(self._entries)
