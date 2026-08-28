"""IEEE 1516-2010 backend for the open-source Portico RTI.

Portico (https://github.com/openlvc/portico) provides the ``hla.rti1516e``
Java API used by :mod:`~pyjevsim.hla.backends.pitch`. This adapter subclasses
the Pitch implementation and handles two Portico-specific differences:
``HLAunicodeString`` encoding and receive-order reflection delivery.

The backend is registered lazily as ``"portico"``. Using it requires JPype,
a compatible JVM, and ``portico.jar`` on the classpath. Portico does not use a
Pitch-style central CRC process.

String representation
---------------------
IEEE 1516-2010 represents ``HLAunicodeString`` as a four-octet big-endian count
of UTF-16 code units followed by the code units. With Portico 2.1.4's supplied
encoder and decoder, the tested string fields arrived empty. The adapter
therefore implements this representation in Python. Unit tests compare the
result with an independent big-endian reference.

Receive-order delivery
----------------------
In the tested Portico 2.1.4 configuration, attribute reflections use the
receive-order ``reflectAttributeValues`` overload without ``LogicalTime``.
They can arrive asynchronously relative to a time-advance grant.

The adapter maps one caller tick to three RTI sub-steps. It buffers reflections
and releases them before the sub-step that allows a peer to publish for the
next caller tick. This keeps next-tick data out of the current tick. Portico
does not signal when the current tick's reflection batch is complete, so the
adapter waits for inbound activity to remain idle for ``quiet`` seconds, up to
``settle`` seconds. A sufficiently late reflection may still move to the next
caller tick; Portico trajectory comparison therefore depends on this timing
assumption.

The configured ``lookahead`` remains the default outbound timestamp offset in
caller ticks. The HLA regulating interval is one RTI sub-step, or one third of
a caller tick.
"""

from __future__ import annotations

import struct
import threading
import time
from typing import Any

from ..registry import register_rti
from ..transport import RTICapabilities
from .pitch import PitchTransport

#: FOM datatype spellings routed through the standard-conformant codec below.
_STRING_TYPES = frozenset(("string", "unicode"))


# ------------------------------------------------- IEEE 1516-2010 HLAunicodeString


def encode_unicode_string(value: str) -> bytes:
    """Encode ``value`` as an IEEE 1516-2010 ``HLAunicodeString``.

    Layout: ``uint32be`` count of UTF-16 code units, then the code units in
    big-endian order. Characters outside the BMP occupy two code units, so
    the count is derived from the encoded length rather than ``len(value)``.
    """
    body = str(value).encode("utf-16-be")
    return struct.pack(">I", len(body) // 2) + body


def decode_unicode_string(raw: bytes) -> str:
    """Decode an IEEE 1516-2010 ``HLAunicodeString`` back to ``str``."""
    if len(raw) < 4:
        raise ValueError("HLAunicodeString shorter than its 4-octet length prefix")
    (units,) = struct.unpack(">I", raw[:4])
    end = 4 + 2 * units
    if len(raw) < end:
        raise ValueError(
            f"HLAunicodeString declares {units} code units but carries "
            f"{(len(raw) - 4) // 2}"
        )
    return raw[4:end].decode("utf-16-be")


# ------------------------------------------------------------- the transport


class PorticoTransport(PitchTransport):
    """RTIConnector backed by the open-source Portico RTI (IEEE 1516-2010).

    Identical to :class:`~pyjevsim.hla.backends.pitch.PitchTransport` except
    for the ``string`` field codec and the time axis; see the module
    docstring for why each is needed.

    Extra keyword arguments:
        settle: upper bound, in seconds, on the wait for Portico to
            dispatch the tick's receive-order reflections.
        quiet: how long the inbound stream must be idle before that wait
            ends early. The normal cost per tick is ``quiet``; ``settle`` is
            only reached on a loaded machine.

    Raising either only costs wall-clock time: reflections are released to the
    models before any peer is let past the tick, so a longer wait can never
    pull the next tick in.

    Inbound events are delivered from :meth:`request_time_advance`, not from
    the RTI callback thread. A caller that never advances time never sees them.
    """

    capabilities = RTICapabilities(
        name="portico",
        time_management=True,
        timestamp_ordered=False,     # Portico reflects in receive order
        interactions=True,
        object_attributes=True,
        default_lookahead=1.0,
    )

    #: RTI time units per caller tick: data, sync, move-on (see below).
    _RTI_SCALE = 3.0

    #: Polling interval of the inter-sub-step wait, in seconds.
    _SETTLE_POLL = 0.002

    def __init__(self, *args, settle: float = 2.0, quiet: float = 0.25,
                 **kwargs) -> None:
        # All set before _boot_jvm() (called from the base __init__) can
        # dispatch a callback.
        self._settle = float(settle)
        self._quiet = float(quiet)
        self._inbox: list = []
        self._inbox_lock = threading.Lock()
        self._rx_count = 0
        super().__init__(*args, **kwargs)

    # ----------------------------------------------------- inbound buffering

    def _emit(self, *args) -> None:
        """Buffer instead of delivering; :meth:`_release_inbox` delivers."""
        with self._inbox_lock:
            self._inbox.append(args)
            # Counted so _settle_inbound can tell "still arriving" from "idle".
            self._rx_count += 1

    def _release_inbox(self) -> None:
        """Hand every buffered reflection to the models, in arrival order."""
        with self._inbox_lock:
            pending, self._inbox = self._inbox, []
        for event in pending:
            super()._emit(*event)

    def _encode_value(self, datatype: str, value: Any):
        if datatype.lower() in _STRING_TYPES:
            jpype = self._jpype
            return jpype.JArray(jpype.JByte)(encode_unicode_string(value))
        return super()._encode_value(datatype, value)

    def _decode_value(self, datatype: str, raw):
        if datatype.lower() in _STRING_TYPES:
            return decode_unicode_string(bytes(raw))
        return super()._decode_value(datatype, raw)

    # ---------------------------------------------------- sub-tick time axis

    def _rti_time(self, logical: float) -> float:
        return self._RTI_SCALE * logical

    def _rti_lookahead(self) -> float:
        # One sub-step: the smallest interval that still lets a federate
        # granted the barrier sub-step publish for the next tick.
        return 1.0

    def _do_request_time_advance(self, target: float) -> float:
        """Advance one caller tick as three RTI sub-steps around a settle.

        ``3t``   data    -- granted once every peer has requested ``3t``,
                           which each does only after publishing its
                           tick-``t`` state, so that state is already in
                           flight.
        ``3t+1`` sync    -- granted once every peer has been granted ``3t``.
                           Their publishes preceded their ``3t+1`` requests on
                           the same channel, so per-sender FIFO delivery means
                           this federate's LRC has the data by now; only the
                           hand-off to the federate may still be pending.
        settle           -- wait for that hand-off.
        release inbox    -- everything buffered so far becomes visible to the
                           models. Nothing from tick ``t+1`` can be in it: a
                           peer publishes tick ``t+1`` only after its ``3t+2``
                           grant, and no peer can be granted ``3t+2`` until
                           the next line runs.
        ``3t+2``         -- lets the federation move on, once every peer has
                           released its own inbox.
        """
        step = super()._do_request_time_advance   # PitchTransport's TAR + wait
        base = self._RTI_SCALE * target
        step(base)
        step(base + 1.0)
        self._settle_inbound()
        self._release_inbox()
        step(base + 2.0)
        self._logical_time = target               # keep caller-tick units
        return target

    def _settle_inbound(self) -> None:
        """Wait for Portico's receive-order reflection activity to settle.

        Returns once the inbound stream has been idle for ``quiet``, or after
        ``settle`` at the latest. Longer waits delay the grant loop. Returning
        before every reflection arrives may defer late items to the next
        caller tick.
        """
        if self._settle <= 0:
            return
        now = time.monotonic
        deadline = now() + self._settle
        last, idle_since = self._rx_count, now()
        while now() < deadline:
            time.sleep(self._SETTLE_POLL)
            seen = self._rx_count
            if seen != last:
                last, idle_since = seen, now()
            elif now() - idle_since >= self._quiet:
                return


register_rti("portico", lambda **kw: PorticoTransport(**kw))
