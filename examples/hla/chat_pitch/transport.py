"""PitchTransport — pyjevsim.hla.Transport wrapping the kdx-rti gateway.

Talks to a `kdx_rti.GatewayClient`, which in turn talks to a Java HLA
gateway process that holds an `RTIambassador` connected to a Pitch CRC.

This is a *pedagogical* transport — the chat-federate path is covered;
DDM, ownership, sync points, save/restore are not. For production use,
either extend this transport or pull in a more complete one from the
kdx-rti repo.

Wire flow per kdx-rti's frozen protocol:
- control channel (DEALER): connect / createFederation / joinFederation /
  publishInteractionClass / subscribeInteractionClass / tick / tickGranted
  / resignFederation / disconnect
- data channel out (PUSH): updateAttributeValues / sendInteraction
- data channel in (SUB): reflect / interaction / discover (when time
  management is off; under the nominal D1-amended flow these arrive
  inlined in tickGranted.bufferedMessages)

Time advance is the tick/tickGranted handshake; we drain
bufferedMessages and dispatch them to the registered callback before
returning the granted time.
"""

from __future__ import annotations

import logging
import queue
from typing import Any, Callable

# kdx-rti is an optional runtime dependency — installed via:
#   pip install pyjevsim pyzmq    # base
#   then clone kdx-rti and `pip install -e .` in its python/ dir
# The import is at module top-level so a missing kdx-rti fails loudly
# rather than at first send().
from kdx_rti.envelope import Envelope
from kdx_rti.transport import GatewayClient, GatewayEndpoints

from pyjevsim.hla import HLAAttribute, HLAInteraction

log = logging.getLogger(__name__)

OnReceive = Callable[[str, str, Any, "float | None"], None]


class PitchTransport:
    """Concrete pyjevsim.hla.Transport implementation backed by kdx-rti."""

    def __init__(
        self,
        endpoints: GatewayEndpoints | None = None,
        timeout_s: float = 5.0,
    ) -> None:
        self._endpoints = endpoints or GatewayEndpoints()
        self._timeout_s = float(timeout_s)
        self._cb: OnReceive | None = None

        self._ctrl_q: queue.Queue[Envelope] = queue.Queue()
        self._data_q: queue.Queue[tuple[str, Envelope]] = queue.Queue()
        self._client = GatewayClient(
            endpoints=self._endpoints,
            control_queue=self._ctrl_q,
            data_queue=self._data_q,
        )
        self._client.start()

        # Pump SUB messages on a small thread so they reach the callback
        # outside the request_time_advance critical path. (Under the
        # typical D1 chat profile bufferedMessages arrive inside
        # tickGranted, so this thread is mostly idle, but keeping it
        # ensures correctness when time management is off.)
        import threading
        self._stop = threading.Event()
        self._sub_pump = threading.Thread(
            target=self._sub_loop, name="pitch-sub-pump", daemon=True
        )
        self._sub_pump.start()

    # ----------------------------------------------------- pyjevsim.hla.Transport

    def send(self, binding, payload: Any) -> None:
        """Outbound interaction or attribute update.

        payload is a list (per pyjevsim.hla §2.1): [{"text": ..., "from": ...}].
        We forward the first element as the params/values dict, which is
        what kdx-rti's data envelope expects.
        """
        params = payload[0] if payload and isinstance(payload, list) else {}
        if isinstance(binding, HLAInteraction):
            env = Envelope(
                type="sendInteraction",
                payload={"interactionClass": binding.fom_id, "parameters": params},
            )
            self._client.send_data(env)
            return
        if isinstance(binding, HLAAttribute):
            if binding.object_class is None:
                raise ValueError(
                    f"outbound HLAAttribute {binding!r} requires object_class"
                )
            env = Envelope(
                type="updateAttributeValues",
                payload={
                    "objectClass": binding.object_class,
                    "attributes": params,
                    # Real wire requires an objectInstanceHandle; the example
                    # leaves that to a higher-level caller in production.
                },
            )
            self._client.send_data(env)
            return
        raise TypeError(f"unsupported binding type {type(binding).__name__}")

    def on_receive(self, callback: OnReceive) -> None:
        self._cb = callback

    def request_time_advance(self, target: float) -> float:
        env = Envelope(type="tick", payload={"logicalTime": float(target)})
        self._client.send_control(env)
        # Drain control queue until tickGranted with matching id arrives.
        # Any other envelopes get re-dispatched as inbound.
        while True:
            inbound = self._next_control(timeout_s=self._timeout_s)
            if inbound.type == "tickGranted" and inbound.id == env.id:
                granted = float(inbound.payload.get("logicalTime", target))
                for inner in inbound.payload.get("bufferedMessages", []) or []:
                    self._dispatch_inner(inner)
                return granted
            self._dispatch_control(inbound)

    def close(self) -> None:
        self._stop.set()
        try:
            self._client.close()
        except Exception:
            log.exception("close failed")

    # -------------------------------------------------- lifecycle (called by Federate)

    def join(self, federation: str, federate_name: str, fom_paths: list[str]) -> None:
        self._req("connect", {})
        self._req("createFederation",
                  {"federationName": federation, "fomModules": list(fom_paths)})
        self._req("joinFederation",
                  {"federationName": federation, "federateName": federate_name})
        self._req("enableTimeRegulation", {"lookahead": 0.1})
        self._req("enableTimeConstrained", {})

    def publish(self, binding) -> None:
        if isinstance(binding, HLAInteraction):
            self._req("publishInteractionClass", {"interactionClass": binding.fom_id})
            return
        if isinstance(binding, HLAAttribute):
            self._req("publishObjectClassAttributes",
                      {"objectClass": binding.object_class or binding.fom_id,
                       "attributes": [binding.fom_id.split(".")[-1]]})
            return

    def subscribe(self, binding) -> None:
        if isinstance(binding, HLAInteraction):
            self._req("subscribeInteractionClass", {"interactionClass": binding.fom_id})
            return
        if isinstance(binding, HLAAttribute):
            self._req("subscribeObjectClassAttributes",
                      {"objectClass": binding.object_class or binding.fom_id,
                       "attributes": [binding.fom_id.split(".")[-1]]})
            return

    def resign(self) -> None:
        try:
            self._req("resignFederation", {})
            self._req("disconnect", {})
        except Exception:
            log.exception("resign sequence failed (gateway may already be down)")

    # ------------------------------------------------------ private helpers

    def _req(self, type_: str, payload: dict) -> Envelope:
        """Send a control envelope and wait for the matching response."""
        env = Envelope(type=type_, payload=payload)
        self._client.send_control(env)
        # Drain until we either see the success envelope (correlation id
        # match) or an error.
        while True:
            inbound = self._next_control(timeout_s=self._timeout_s)
            if inbound.id == env.id:
                if inbound.type == "error":
                    raise RuntimeError(
                        f"gateway error on {type_}: {inbound.payload!r}"
                    )
                return inbound
            # Unrelated inbound (e.g. an async announce) — dispatch it.
            self._dispatch_control(inbound)

    def _next_control(self, *, timeout_s: float) -> Envelope:
        try:
            return self._ctrl_q.get(timeout=timeout_s)
        except queue.Empty as e:
            raise TimeoutError(
                f"no control envelope from gateway within {timeout_s}s"
            ) from e

    def _dispatch_control(self, env: Envelope) -> None:
        # Any control envelope that's not a direct response can carry an
        # async data event (e.g. announceSynchronizationPoint). For the
        # chat example we only forward inbound interactions/reflects via
        # bufferedMessages on tickGranted, so this is mostly a sink.
        log.debug("unrouted control envelope: type=%s id=%s",
                  env.type, env.id)

    def _dispatch_inner(self, inner: dict) -> None:
        """Translate a bufferedMessages entry into the callback shape."""
        if not isinstance(inner, dict) or self._cb is None:
            return
        t = inner.get("type")
        payload = inner.get("payload", {}) or {}
        timestamp = inner.get("timestamp")
        if t == "interaction":
            self._cb("interaction",
                     payload.get("interactionClass", "?"),
                     [payload.get("parameters", {})],
                     timestamp)
        elif t == "reflect":
            self._cb("attribute",
                     payload.get("objectClass", "?") + "." +
                     next(iter(payload.get("attributes", {}) or {"?": None}).keys()),
                     [payload.get("attributes", {})],
                     timestamp)

    def _sub_loop(self) -> None:
        while not self._stop.is_set():
            try:
                topic, env = self._data_q.get(timeout=0.2)
            except queue.Empty:
                continue
            self._dispatch_inner({
                "type": env.type,
                "payload": env.payload,
                "timestamp": env.timestamp,
            })
