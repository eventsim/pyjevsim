"""GortiTransport — pyjevsim.hla.Transport backed by gorti's pysdk.

Wraps `rti1516e.Rti1516eAmbassador` (Layer 2, callback-shaped). Each
inbound `receiveInteraction` / `reflectAttributeValues` callback is
forwarded to the pyjevsim `_HLARouter` via the registered
`on_receive` callable.

Time advance uses `nextMessageRequest`. The ambassador delivers a
`timeAdvanceGrant` callback with the granted time; we block on a
condition variable until the grant arrives, drain any inbound events
queued during the wait, and return the granted time to the federate.

This transport is intentionally minimal — interactions only, no
object instances. Extend for production use.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from rti1516e.standard import Rti1516eAmbassador

from pyjevsim.hla import HLAAttribute, HLAInteraction

log = logging.getLogger(__name__)

OnReceive = Callable[[str, str, Any, "float | None"], None]


class _ChatAmbassador(Rti1516eAmbassador):
    """Ambassador subclass that forwards inbound events to a callback."""

    def __init__(self) -> None:
        super().__init__()
        self.cb: OnReceive | None = None
        self._grant_cv = threading.Condition()
        self._granted_time: float | None = None

    # --- inbound callbacks ----------------------------------------------

    def receiveInteraction(  # noqa: N802 — IEEE 1516.1 name
        self,
        class_name: str,
        parameters: dict[str, Any],
        timestamp: float | None,
    ) -> None:
        if self.cb is not None:
            self.cb("interaction", class_name, [dict(parameters)], timestamp)

    def reflectAttributeValues(  # noqa: N802 — IEEE 1516.1 name
        self,
        object_handle: int,
        values: dict[str, Any],
        timestamp: float | None,
    ) -> None:
        if self.cb is not None:
            # We surface attribute updates with fom_id = "<object_handle>"
            # for the example; a richer transport would resolve the
            # object class via discoverObjectInstance bookkeeping.
            self.cb("attribute", str(object_handle), [dict(values)], timestamp)

    def timeAdvanceGrant(self, time: float) -> None:  # noqa: N802
        with self._grant_cv:
            self._granted_time = float(time)
            self._grant_cv.notify_all()

    # --- helper used by the transport -----------------------------------

    def wait_for_grant(self, timeout_s: float) -> float:
        with self._grant_cv:
            if self._granted_time is None:
                self._grant_cv.wait(timeout=timeout_s)
            if self._granted_time is None:
                raise TimeoutError(
                    f"timeAdvanceGrant did not arrive within {timeout_s}s"
                )
            granted = self._granted_time
            self._granted_time = None
            return granted


class GortiTransport:
    """Concrete pyjevsim.hla.Transport implementation backed by gorti."""

    def __init__(self, url: str = "memory://chat-rti", timeout_s: float = 5.0) -> None:
        self._url = url
        self._timeout_s = float(timeout_s)
        self._cb: OnReceive | None = None
        self._amb = _ChatAmbassador()
        self._amb.connect(self._amb, url)

    # ----------------------------------------------------- pyjevsim.hla.Transport

    def send(self, binding, payload: Any) -> None:
        params = payload[0] if payload and isinstance(payload, list) else {}
        if isinstance(binding, HLAInteraction):
            self._amb.sendInteraction(binding.fom_id, dict(params))
            return
        if isinstance(binding, HLAAttribute):
            if binding.object_class is None:
                raise ValueError(
                    f"outbound HLAAttribute {binding!r} requires object_class"
                )
            # The example doesn't track object handles; production code
            # would map a port → handle via registerObjectInstance.
            raise NotImplementedError(
                "object instance management not implemented in this example"
            )
        raise TypeError(f"unsupported binding type {type(binding).__name__}")

    def on_receive(self, callback: OnReceive) -> None:
        self._cb = callback
        self._amb.cb = callback

    def request_time_advance(self, target: float) -> float:
        self._amb.nextMessageRequest(float(target))
        return self._amb.wait_for_grant(timeout_s=self._timeout_s)

    def close(self) -> None:
        try:
            self._amb.disconnect()
        except Exception:
            log.exception("disconnect failed")

    # ----------------------------------------------- lifecycle (called by Federate)

    def join(self, federation: str, federate_name: str, fom_paths: list[str]) -> None:
        self._amb.createFederationExecution(federation, list(fom_paths))
        self._amb.joinFederationExecution(federate_name, federation)
        self._amb.enableTimeRegulation(0.1)
        self._amb.enableTimeConstrained()

    def publish(self, binding) -> None:
        if isinstance(binding, HLAInteraction):
            self._amb.publishInteractionClass(binding.fom_id)
            return
        if isinstance(binding, HLAAttribute):
            attrs = [binding.fom_id.split(".")[-1]]
            self._amb.publishObjectClassAttributes(
                binding.object_class or binding.fom_id, attrs
            )

    def subscribe(self, binding) -> None:
        if isinstance(binding, HLAInteraction):
            self._amb.subscribeInteractionClass(binding.fom_id)
            return
        if isinstance(binding, HLAAttribute):
            attrs = [binding.fom_id.split(".")[-1]]
            self._amb.subscribeObjectClassAttributes(
                binding.object_class or binding.fom_id, attrs
            )

    def resign(self) -> None:
        try:
            self._amb.resignFederationExecution()
        except Exception:
            log.exception("resign failed")
