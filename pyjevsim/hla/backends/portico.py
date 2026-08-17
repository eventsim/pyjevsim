"""PorticoTransport — IEEE 1516-2010 backend for the open-source Portico RTI.

Portico (https://github.com/openlvc/portico) implements the same standard
``hla.rti1516e`` Java API that :mod:`~pyjevsim.hla.backends.pitch` programs
against, and needs no central RTI component (CRC): every LRC discovers its
peers over JGroups. :class:`PorticoTransport` therefore reuses the whole
Pitch transport -- connect/join, declaration management, object registration,
TSO send, TAR/grant loop -- and overrides only what Portico gets wrong: the
encoding of ``string`` fields, and the time axis (see below).

Registered (lazily) under the name ``"portico"``::

    from pyjevsim.hla import create_rti
    tx = create_rti("portico",
                    federation="PingPong",
                    federate="ping",
                    fom="examples/hla_pingpong/fom/PingPong.xml",
                    fom_map=PINGPONG_FOM_MAP,
                    jvm_path=r"C:\\Program Files\\...\\jvm.dll",   # optional
                    classpath=[r"C:\\...\\portico-2.1.4\\lib\\portico.jar"])

Requirements (NOT needed to import this module -- only to *use* it):
  * ``pip install jpype1`` matching your Python and Java versions;
  * a Portico distribution; its ``lib/portico.jar`` on the classpath and
    ``RTI_HOME`` pointing at the distribution root.

No CRC process is required: the first federate to create the federation
elects itself co-ordinator.

HLAunicodeString
----------------
IEEE 1516-2010 encodes ``HLAunicodeString`` as a 4-octet big-endian count of
UTF-16 code units followed by the code units in big-endian order. Portico
2.1.4 gets this wrong in both directions:

  * ``getEncodedLength()`` returns ``4 + 2 * value.getBytes("UTF-16").length``
    -- double the correct size (``String.getBytes("UTF-16")`` already emits
    two octets per code unit, plus a byte-order mark), so ``toByteArray()``
    hands back a buffer padded with trailing zero octets;
  * ``decode()`` reads the element count with ``ByteWrapper.get()`` (a single
    octet) instead of ``getInt()`` (four octets), so every string whose
    length fits in the low-order octet decodes as ``""``.

The net effect is silent data loss: numeric fields survive, string fields
arrive empty. Rather than depend on the RTI's ``EncoderFactory`` for this
datatype, the backend encodes and decodes ``HLAunicodeString`` in Python
according to the standard. The resulting octets are byte-for-byte identical
to those produced by Pitch pRTI 5.5.2, so a pyjevsim federate on Portico
stays wire-compatible with a pyjevsim federate on Pitch.

Receive-order delivery
----------------------
Portico 2.1.4 hands every attribute reflection to the federate ambassador
through the *receive-order* ``reflectAttributeValues`` overload -- the one
without a ``LogicalTime`` -- even when the FOM declares
``<order>TimeStamp</order>`` and both federates are time regulating and time
constrained. Reflections therefore arrive whenever the network delivers
them, tens of milliseconds after the time-advance grant that is supposed to
follow them, and a federate that reads its peers' state immediately after a
grant sees either the current or the previous tick depending on wall-clock
luck.

The backend rebuilds the barrier out of the one thing Portico does honour,
time regulation: three RTI sub-steps per caller tick (see
:meth:`PorticoTransport._do_request_time_advance`). Reflections are held in
a buffer as they arrive and released to the models at a single point, chosen
so that nothing a peer publishes for tick ``t+1`` can ever be visible during
tick ``t`` -- the release happens before the sub-step that lets any peer move
on. That half of the ordering is exact, not probabilistic.

The other half is not. Portico offers no signal that a tick's reflections
are complete, so before releasing the buffer the backend waits for the
inbound stream to fall idle for ``quiet`` seconds (capped at ``settle``).
Measured dispatch latency on a single host is 15-40 ms and the default
``quiet`` is 0.25 s, but a long enough gap inside one tick's burst -- on a
loaded machine, say -- can still end the wait early and defer a reflection to
the next tick. Raise ``quiet`` if a run diverges. Exact trace equivalence on
Portico therefore rests on a timing assumption; on an RTI that honours
time-stamp order it does not.

The sub-tick axis is internal: ``request_time_advance`` still takes and
returns caller ticks, and ``lookahead`` is still expressed in ticks.
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
        """Wait out Portico's reflection dispatch latency.

        Returns once the inbound stream has been idle for ``quiet``, or after
        ``settle`` at the latest. Waiting too long is harmless -- the buffer
        is released afterwards and no peer moves on until it is -- so the only
        failure mode is ending too early.
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
