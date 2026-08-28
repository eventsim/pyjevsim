"""Transport interfaces and the in-process loopback backend.

``Transport`` defines the methods used by the executor. ``RTIConnector`` adds
lifecycle handling and codec dispatch for concrete RTI adapters.
``RTICapabilities`` describes optional backend services, and ``_HLARouter``
dispatches received events to subscribed executors.

See ``docs/hla/specification.md`` for the runtime contract and
``docs/hla/rti_interface.md`` for backend implementation guidance.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Protocol, runtime_checkable

# callback(kind, fom_id, payload, timestamp)
OnReceive = Callable[[str, str, Any, "float | None"], None]


# --------------------------------------------------------------- capabilities


@dataclass(frozen=True)
class RTICapabilities:
    """Services reported by an RTI backend.

    These flags are descriptive. Applications should also check the backend's
    documented service matrix before relying on an optional HLA service.
    """

    name: str = "unknown"
    time_management: bool = False        # regulating/constrained logical time
    timestamp_ordered: bool = False      # TSO delivery vs receive-order (RO)
    interactions: bool = True            # sendInteraction / receiveInteraction
    object_attributes: bool = False      # update/reflect attribute values
    ddm: bool = False                    # data distribution management
    ownership: bool = False              # ownership management
    default_lookahead: "float | None" = None


# --------------------------------------------------------------------- codec


@runtime_checkable
class Codec(Protocol):
    """FOM (de)serialization, decoupled from the transport.

    ``encode`` turns the pyjevsim-side ``payload`` (always the list returned
    by ``SysMessage.retrieve()``) into whatever the backend ships on the
    wire. ``decode`` is the inverse for inbound events. The default
    :class:`IdentityCodec` passes objects through unchanged (loopback /
    in-process backends); live RTIs supply a codec that maps to the FOM
    datatypes (e.g. HLA 1516e ``HLAfixedRecord`` via the EncoderFactory).
    """

    def encode(self, binding, payload: Any) -> Any: ...
    def decode(self, kind: str, fom_id: str, wire: Any) -> Any: ...


class IdentityCodec:
    """Pass values through unchanged for in-process backends."""

    def encode(self, binding, payload: Any) -> Any:
        return payload

    def decode(self, kind: str, fom_id: str, wire: Any) -> Any:
        return wire


# ----------------------------------------------------------- structural type


class Transport(Protocol):
    """Structural interface used by HLA executors.

    Existing duck-typed transports may implement this protocol directly.
    New RTI adapters normally subclass :class:`RTIConnector` to reuse its
    lifecycle methods.
    """

    def send(self, binding, payload: Any) -> None: ...
    def on_receive(self, callback: OnReceive) -> None: ...
    def request_time_advance(self, target: float) -> float: ...
    def close(self) -> None: ...


# ----------------------------------------------------------- nominal base


class RTIConnector(ABC):
    """Base class for RTI adapters.

    Subclasses implement the RTI-specific ``_do_*`` operations:

    Required (abstract):
        * ``_do_send(binding, wire, timestamp)``
        * ``_do_request_time_advance(target) -> granted``

    Optional lifecycle hooks have no-op defaults:
        * ``_do_join(federation, federate_name, fom_paths)``
        * ``_do_publish(binding)`` / ``_do_subscribe(binding)``
        * ``_do_resign()`` / ``_do_close()``

    A backend passes received wire values to :meth:`_emit`. The connector
    decodes the value and calls the registered receiver. Backends that call
    :meth:`_emit` from an RTI callback thread rely on the executor's
    thread-safe external-event insertion.
    """

    #: Backends override with their own capability set.
    capabilities: RTICapabilities = RTICapabilities()

    def __init__(self, codec: "Codec | None" = None) -> None:
        self._codec: Codec = codec or IdentityCodec()
        self._callback: "OnReceive | None" = None
        self._joined = False
        self._closed = False

    # ------------------------------------------------------------ data plane

    def send(self, binding, payload: Any, *, timestamp: "float | None" = None) -> None:
        """Publish an outbound binding's payload to the RTI.

        ``in`` bindings are ignored. ``payload`` is the list returned by
        ``SysMessage.retrieve()``. For timestamp-ordered backends,
        ``timestamp`` is the logical send time; ``None`` requests
        receive-order delivery.
        """
        if binding.direction not in ("out", "inout"):
            return
        wire = self._codec.encode(binding, payload)
        self._do_send(binding, wire, timestamp)

    def on_receive(self, callback: OnReceive) -> None:
        """Register the single inbound subscriber (re-registering replaces)."""
        self._callback = callback

    def _emit(self, kind: str, fom_id: str, wire: Any,
              timestamp: "float | None" = None) -> None:
        """Backend RX hook: decode wire and dispatch to the callback."""
        cb = self._callback
        if cb is None:
            return
        payload = self._codec.decode(kind, fom_id, wire)
        cb(kind, fom_id, payload, timestamp)

    # ------------------------------------------------------------ time plane

    def request_time_advance(self, target: float) -> float:
        """Block until the RTI grants; return the granted logical time."""
        return self._do_request_time_advance(target)

    # ------------------------------------------------------------- lifecycle

    def join(self, federation: str, federate_name: str, fom_paths) -> None:
        if self._joined:
            raise RuntimeError("join() called twice")
        self._do_join(federation, federate_name, fom_paths)
        self._joined = True

    def publish(self, binding) -> None:
        self._require_joined("publish")
        if binding.direction not in ("out", "inout"):
            raise ValueError(
                "publish() requires a binding with direction 'out' or 'inout'"
            )
        self._do_publish(binding)

    def subscribe(self, binding) -> None:
        self._require_joined("subscribe")
        if binding.direction not in ("in", "inout"):
            raise ValueError(
                "subscribe() requires a binding with direction 'in' or 'inout'"
            )
        self._do_subscribe(binding)

    def resign(self) -> None:
        if not self._joined:
            return
        self._do_resign()
        self._joined = False

    def close(self) -> None:
        if self._closed:
            return
        if self._joined:
            try:
                self.resign()
            except Exception:
                pass
        self._do_close()
        self._closed = True

    @property
    def joined(self) -> bool:
        return self._joined

    def _require_joined(self, op: str) -> None:
        if not self._joined:
            raise RuntimeError(f"{op}() called before join()")

    # ----------------------------------------------------- RTI-specific hooks

    @abstractmethod
    def _do_send(self, binding, wire: Any, timestamp: "float | None") -> None:
        """Ship an encoded outbound binding to the RTI."""

    @abstractmethod
    def _do_request_time_advance(self, target: float) -> float:
        """Issue a time-advance request; return the granted logical time."""

    # Loopback-style backends can use these no-op lifecycle hooks.
    def _do_join(self, federation: str, federate_name: str, fom_paths) -> None:
        pass

    def _do_publish(self, binding) -> None:
        pass

    def _do_subscribe(self, binding) -> None:
        pass

    def _do_resign(self) -> None:
        pass

    def _do_close(self) -> None:
        pass


# ------------------------------------------------------------- loopback impl


class LoopbackTransport(RTIConnector):
    """Mirror outbound values to the receiver in the current process.

    This backend has no federation-wide time coordination. A time-advance
    request returns its target unchanged, and lifecycle hooks are no-ops.
    """

    capabilities = RTICapabilities(
        name="loopback",
        time_management=False,
        timestamp_ordered=False,
        interactions=True,
        object_attributes=True,
    )

    def _do_send(self, binding, wire: Any, timestamp: "float | None") -> None:
        self._emit(binding.kind, binding.fom_id, wire, timestamp)

    def _do_request_time_advance(self, target: float) -> float:
        return target


# ------------------------------------------------------------------ router


class _HLARouter:
    """Dispatch transport events to subscribed HLA executors.

    One router is attached to each transport. More than one executor may
    subscribe to the same ``(kind, fom_id)`` pair.
    """

    def __init__(self, transport) -> None:
        self._transport = transport
        self._subs: dict[tuple[str, str], list] = {}
        transport.on_receive(self._dispatch)

    def subscribe(self, kind: str, fom_id: str, executor) -> None:
        self._subs.setdefault((kind, fom_id), []).append(executor)

    def unsubscribe(self, kind: str, fom_id: str, executor) -> None:
        key = (kind, fom_id)
        lst = self._subs.get(key)
        if not lst:
            return
        try:
            lst.remove(executor)
        except ValueError:
            return
        if not lst:
            del self._subs[key]

    def _dispatch(self, kind: str, fom_id: str, payload: Any,
                  timestamp: "float | None") -> None:
        for ex in tuple(self._subs.get((kind, fom_id), ())):
            ex._on_rti_event(kind, fom_id, payload, timestamp)
