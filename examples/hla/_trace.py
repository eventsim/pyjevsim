"""Transport decorator that writes a normalized event log.

The log covers lifecycle, data, and time-advance calls. It omits wall-clock
timestamps and correlation IDs so runs can be compared without those
run-specific values.

Wire format (one event per line, fields are space-separated key=value):

    JOIN federation=<name> federate=<name> fom=<comma-sep-paths>
    PUBLISH kind=<kind> fom=<fom_id>
    SUBSCRIBE kind=<kind> fom=<fom_id>
    TAR target=<logical-time>
    GRANT granted=<logical-time>
    SEND kind=<kind> fom=<fom_id> payload=<canonical-json>
    RECV kind=<kind> fom=<fom_id> payload=<canonical-json>
    RESIGN
    CLOSE

Logical target and grant values are included. A difference between two logs
can result from backend time management as well as application behavior.

Payload keys are sorted and whitespace is removed. Logical-time floats use
``%.6g`` formatting.
"""

from __future__ import annotations

import json
import sys
import threading
from typing import Any, Callable, IO

OnReceive = Callable[[str, str, Any, "float | None"], None]


def _canonical_json(payload: Any) -> str:
    """Render a payload as canonical JSON for stable diffing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      default=str)


def _fmt_time(t: float) -> str:
    return f"{float(t):.6g}"


class TracingTransport:
    """Wrap a transport and record its calls.

    The wrapped transport carries RTI traffic. Exceptions from it propagate
    to the caller.
    """

    def __init__(self, inner, sink: "IO[str] | None" = None) -> None:
        self._inner = inner
        self._sink: IO[str] = sink if sink is not None else sys.stdout
        self._lock = threading.Lock()
        self._user_cb: OnReceive | None = None
        # Keep the interceptor registered while allowing the user callback to
        # be replaced.
        self._inner.on_receive(self._on_receive_wrapper)

    # ------------------------------------------------------ tracing helpers

    def _emit(self, line: str) -> None:
        with self._lock:
            self._sink.write(line + "\n")
            self._sink.flush()

    # ----------------------------------------------------- pyjevsim.hla.Transport

    def send(self, binding, payload: Any) -> None:
        self._emit(
            f"SEND kind={binding.kind} fom={binding.fom_id} "
            f"payload={_canonical_json(payload)}"
        )
        self._inner.send(binding, payload)

    def on_receive(self, callback: OnReceive) -> None:
        # The inner transport continues to call _on_receive_wrapper.
        self._user_cb = callback

    def request_time_advance(self, target: float) -> float:
        self._emit(f"TAR target={_fmt_time(target)}")
        granted = self._inner.request_time_advance(target)
        self._emit(f"GRANT granted={_fmt_time(granted)}")
        return granted

    def close(self) -> None:
        self._emit("CLOSE")
        self._inner.close()

    # ----------------------------------------------- lifecycle (delegated)

    def join(self, federation: str, federate_name: str, fom_paths) -> None:
        self._emit(
            f"JOIN federation={federation} federate={federate_name} "
            f"fom={','.join(fom_paths)}"
        )
        self._inner.join(federation, federate_name, fom_paths)

    def publish(self, binding) -> None:
        self._emit(f"PUBLISH kind={binding.kind} fom={binding.fom_id}")
        self._inner.publish(binding)

    def subscribe(self, binding) -> None:
        self._emit(f"SUBSCRIBE kind={binding.kind} fom={binding.fom_id}")
        self._inner.subscribe(binding)

    def resign(self) -> None:
        self._emit("RESIGN")
        self._inner.resign()

    # ---------------------------------------------------- inbound interceptor

    def _on_receive_wrapper(self, kind: str, fom_id: str, payload: Any,
                            timestamp: float | None) -> None:
        self._emit(
            f"RECV kind={kind} fom={fom_id} "
            f"payload={_canonical_json(payload)}"
        )
        if self._user_cb is not None:
            self._user_cb(kind, fom_id, payload, timestamp)
