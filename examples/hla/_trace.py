"""TracingTransport — decorator that emits a canonical event sequence.

Wraps any pyjevsim.hla.Transport. Logs every call (lifecycle + data
+ time advance) as one line in a stable, RTI-agnostic format with
no wallclock timestamps and no correlation IDs. The output of two
runs against semantically identical RTIs (e.g. Pitch and gorti)
should `diff` to the empty set — any line that differs is a
semantics divergence worth investigating.

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

Logical time values (target, granted) ARE included — they are part
of the HLA semantics under test, and any difference between RTIs
indicates a time-management divergence. Wallclock timestamps are
NOT included; correlation IDs are NOT included.

Payloads are serialized with sorted keys and no whitespace so that
dict iteration order does not affect the output. Floats are formatted
with %.6g so platform-specific float-repr differences don't leak.
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
    """Decorator wrapping any Transport with a canonical event log.

    The wrapped transport (`inner`) carries the actual RTI traffic;
    this class only observes and prints. Any exception from `inner`
    propagates unchanged.
    """

    def __init__(self, inner, sink: "IO[str] | None" = None) -> None:
        self._inner = inner
        self._sink: IO[str] = sink if sink is not None else sys.stdout
        self._lock = threading.Lock()
        self._user_cb: OnReceive | None = None
        # Register our wrapper with the inner transport. Subsequent
        # on_receive() calls from pyjevsim re-target self._user_cb;
        # the inner transport keeps seeing our wrapper.
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
        # pyjevsim's _HLARouter calls this once at construction. Replace
        # the user callback; keep our wrapper as the inner's callback.
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
