"""Federate — lifecycle helper + HLA_TIME grant loop.

Spec: docs/hla/specification.md §5.

Federate is a thin wrapper that delegates lifecycle calls (join, publish,
subscribe, resign) to the transport and drives the request_time_advance
↔ step loop.
"""

from __future__ import annotations


class Federate:
    def __init__(self, sys_executor, transport) -> None:
        self._sys = sys_executor
        self._tx = transport
        self._joined = False

    def join(self, federation_name: str, federate_name: str, fom_paths) -> None:
        self._tx.join(federation_name, federate_name, fom_paths)
        self._joined = True

    def publish(self, binding) -> None:
        if not self._joined:
            raise RuntimeError("publish() called before join()")
        self._tx.publish(binding)

    def subscribe(self, binding) -> None:
        if not self._joined:
            raise RuntimeError("subscribe() called before join()")
        self._tx.subscribe(binding)

    def resign(self) -> None:
        self._tx.resign()
        self._joined = False

    def run_until(self, end_time: float, lookahead: float) -> None:
        if lookahead <= 0:
            raise ValueError(f"lookahead must be > 0, got {lookahead!r}")
        while self._sys.global_time < end_time:
            target = min(self._sys.global_time + lookahead, end_time)
            granted = self._tx.request_time_advance(target)
            self._sys.step(granted)
