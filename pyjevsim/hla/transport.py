"""RTI-agnostic transport interface + LoopbackTransport + _HLARouter.

Spec: docs/hla/specification.md §2 (data/time/lifecycle contract).
Interface design: docs/hla/rti_interface.md (how to add a new RTI backend).

Layering
--------
``Transport``        — minimal *structural* type (Protocol). Anything with
                       ``send / on_receive / request_time_advance / close``
                       satisfies it. Kept for back-compat and duck-typed
                       test stubs.
``RTIConnector``     — the *nominal* base class new backends should extend.
                       It implements all the common plumbing (codec hook,
                       single-callback dispatch, join/resign state machine,
                       idempotent close) as template methods and leaves only
                       the RTI-specific operations (``_do_*``) abstract. A
                       new RTI (CERTI, Portico, OpenRTI, MAK, Pitch, ...)
                       becomes ~5 small methods.
``RTICapabilities``  — feature flags a backend advertises so callers can
                       adapt (TSO? object attributes? time management?).
``Codec``            — pluggable FOM (de)serialization, orthogonal to the
                       wire transport. The same RTI can carry different
                       FOMs; the same FOM codec can be reused across RTIs.
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
    """What an RTI backend can do.

    Callers (and HLAExecutor / Federate) may consult these to adapt or to
    fail fast — e.g. warn when timestamps are supplied but the backend
    cannot deliver time-stamp-ordered (TSO), or when an ``HLAAttribute``
    binding is used against an interactions-only transport.
    """

    name: str = "unknown"
    time_management: bool = False        # regulating/constrained TAR/NER
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
    in-process backends); real RTIs supply a codec that maps to the FOM
    datatypes (e.g. HLA 1516e ``HLAfixedRecord`` via the EncoderFactory).
    """

    def encode(self, binding, payload: Any) -> Any: ...
    def decode(self, kind: str, fom_id: str, wire: Any) -> Any: ...


class IdentityCodec:
    """Pass-through codec. Used by in-process backends (loopback)."""

    def encode(self, binding, payload: Any) -> Any:
        return payload

    def decode(self, kind: str, fom_id: str, wire: Any) -> Any:
        return wire


# ----------------------------------------------------------- structural type


class Transport(Protocol):
    """Minimal structural transport contract (spec §2.1).

    Retained for back-compat and for duck-typed test stubs. New backends
    should subclass :class:`RTIConnector` instead, which guarantees the
    full lifecycle surface (join/publish/subscribe/resign) that
    :class:`~pyjevsim.hla.federate.Federate` delegates to.
    """

    def send(self, binding, payload: Any) -> None: ...
    def on_receive(self, callback: OnReceive) -> None: ...
    def request_time_advance(self, target: float) -> float: ...
    def close(self) -> None: ...


# ----------------------------------------------------------- nominal base


class RTIConnector(ABC):
    """Base class for RTI backends — the recommended extension point.

    Implements the common mechanics so a concrete backend only has to
    provide the RTI-specific ``_do_*`` operations:

    Required (abstract):
        * ``_do_send(binding, wire, timestamp)``
        * ``_do_request_time_advance(target) -> granted``

    Optional (default no-op — override if the RTI needs them):
        * ``_do_join(federation, federate_name, fom_paths)``
        * ``_do_publish(binding)`` / ``_do_subscribe(binding)``
        * ``_do_resign()`` / ``_do_close()``

    Inbound path: the backend's receive thread calls :meth:`_emit` with
    the raw wire object; the connector decodes it and forwards to the
    single registered callback (the ``_HLARouter``). ``_emit`` may be
    invoked from any thread — the downstream
    ``SysExecutor.insert_external_event`` is lock-protected.
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

        Direction is enforced here: only ``out``/``inout`` bindings are
        shipped (an ``in`` binding handed to ``send`` is dropped, matching
        spec §2.2). ``payload`` is always the list from
        ``SysMessage.retrieve()``. ``timestamp`` carries the logical send
        time for TSO-capable backends (``None`` => receive-order).
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
        self._do_publish(binding)

    def subscribe(self, binding) -> None:
        self._require_joined("subscribe")
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

    # Optional lifecycle hooks — default no-ops so trivial backends
    # (loopback, in-process) need not implement them.
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
    """In-process transport: mirrors out→in to the registered callback.

    Test / demo backend. ``send`` on an ``out``/``inout`` binding is
    delivered straight back through ``_emit`` (the router then fans it out
    to subscribed executors). ``request_time_advance`` is identity (no flow
    control). Lifecycle methods are inherited no-ops.
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
    """Single subscriber on a Transport; demultiplexes to HLAExecutors.

    Spec §2.3. One per transport. Multiple executors may subscribe to
    the same (kind, fom_id); all receive each event.
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
