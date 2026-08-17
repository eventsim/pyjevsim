"""PorticoTransport — IEEE 1516-2010 backend for the open-source Portico RTI.

Portico (https://github.com/openlvc/portico) implements the same standard
``hla.rti1516e`` Java API that :mod:`~pyjevsim.hla.backends.pitch` programs
against, and needs no central RTI component (CRC): every LRC discovers its
peers over JGroups. :class:`PorticoTransport` therefore reuses the whole
Pitch transport -- connect/join, declaration management, object registration,
TSO send, TAR/grant loop -- and overrides exactly one thing: the encoding of
``string`` fields (see `HLAunicodeString` below).

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

The backend narrows this to a one-sided problem by spending three RTI
sub-steps per caller tick (see
:meth:`PorticoTransport._do_request_time_advance`): after the barrier step no
peer can publish for the *next* tick, so nothing from the future can be
dispatched while the caller is processing this one. What remains is the
RTI's unbounded dispatch latency for the *current* tick, which the backend
covers by waiting ``settle`` seconds before returning from the barrier. The
barrier is what makes that wait safe -- waiting longer costs time but can
never let a future tick leak in. Measured dispatch latency on a single host
is 15-40 ms; the default ``settle`` is 0.1 s.

The sub-tick axis is internal: ``request_time_advance`` still takes and
returns caller ticks, and ``lookahead`` is still expressed in ticks.
"""

from __future__ import annotations

import struct
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

    Extra keyword argument:
        settle: seconds to wait after each barrier grant for Portico to
            dispatch the tick's receive-order reflections (default 0.1).
            Raising it only costs wall-clock time; the barrier is what keeps
            the wait from over-reading into the next tick.
    """

    capabilities = RTICapabilities(
        name="portico",
        time_management=True,
        timestamp_ordered=False,     # Portico reflects in receive order
        interactions=True,
        object_attributes=True,
        default_lookahead=1.0,
    )

    #: RTI time units per caller tick: data, barrier, release (see above).
    _RTI_SCALE = 3.0

    def __init__(self, *args, settle: float = 0.1, **kwargs) -> None:
        # Set before _boot_jvm() (called from the base __init__) can dispatch
        # a callback, and before the first time advance defers its release.
        self._release_at: "float | None" = None
        #: Seconds to wait, after the barrier grant, for Portico to dispatch
        #: the current tick's receive-order reflections. Safe to raise.
        self._settle = float(settle)
        super().__init__(*args, **kwargs)

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
        # One sub-step. Any larger and requesting the barrier step would not
        # hold the peer back; any smaller and a granted federate could not
        # publish for the next tick.
        return 1.0

    def _do_request_time_advance(self, target: float) -> float:
        """Advance one caller tick as three RTI sub-steps.

        ``3t``   data     -- granted once every peer has requested ``3t``,
                            which each does only after publishing its
                            tick-``t`` state; per-sender FIFO delivery then
                            puts those reflections ahead of the grant in the
                            LRC queue, so they are dispatched first.
        ``3t+1`` barrier  -- a peer publishes for tick ``t+1`` at ``3t+3``,
                            which it may not do until it is granted ``3t+2``,
                            which in turn waits on this federate requesting
                            ``3t+2``.
        ``3t+2`` release  -- deferred to the *next* call. That deferral is
                            what holds every peer still for the whole of the
                            caller's tick-``t`` processing. Publishing tick
                            ``t+1`` at ``3t+3`` from logical time ``3t+1`` is
                            still legal with a lookahead of one sub-step.
        """
        step = super()._do_request_time_advance   # PitchTransport's TAR + wait
        if self._release_at is not None:
            step(self._release_at)
        base = self._RTI_SCALE * target
        step(base)
        step(base + 1.0)
        if self._settle:
            time.sleep(self._settle)     # dispatch latency, bounded by the barrier
        self._release_at = base + 2.0
        self._logical_time = target               # keep caller-tick units
        return target


register_rti("portico", lambda **kw: PorticoTransport(**kw))
