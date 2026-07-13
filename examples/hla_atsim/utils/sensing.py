"""Snapshot-based sensing primitives for hla_atsim.

Replaces the live ``ObjectDB().items`` reads with a *frozen* per-tick
position snapshot. Detectors read the snapshot instead of live objects so
that the Manuever(writer)/Detector(reader) order within a tick is
irrelevant — reads are always end-of-previous-tick and order-independent
(iteration is sorted by a stable ``sense_id``).

The same mechanism serves both builds:
  * standalone : snapshot fed from the single executor's local items.
  * HLA        : snapshot fed from local items + reflected peer/decoy
                 positions (``RemoteObject`` proxies).
"""


class FrozenProxy:
    """Immutable end-of-tick view of one sensible object."""

    __slots__ = ("sense_id", "kind", "_pos", "_active")

    def __init__(self, sense_id, kind, pos, active):
        self.sense_id = sense_id
        self.kind = kind
        self._pos = tuple(pos)
        self._active = bool(active)

    def get_position(self):
        return self._pos

    def check_active(self):
        return self._active


class RemoteObject:
    """Mutable holder updated by ProxySink from reflected HLA attributes."""

    __slots__ = ("sense_id", "kind", "x", "y", "z", "active")

    def __init__(self, sense_id, kind, x, y, z, active):
        self.sense_id = sense_id
        self.kind = kind
        self.x = x
        self.y = y
        self.z = z
        self.active = active

    def get_position(self):
        return (self.x, self.y, self.z)

    def check_active(self):
        return self.active


class PositionSnapshot:
    """A per-tick, order-independent snapshot keyed by stable ``sense_id``."""

    def __init__(self):
        self._by_id = {}

    def refresh(self, objects):
        """Freeze the given objects' positions/active flags.

        ``objects`` : any objects exposing ``.sense_id``, ``.kind``,
        ``get_position()`` and ``check_active()``.
        """
        self._by_id = {
            o.sense_id: FrozenProxy(o.sense_id, o.kind,
                                    o.get_position(), o.check_active())
            for o in objects
        }

    def get(self, sense_id):
        return self._by_id.get(sense_id)

    def entries(self):
        """Deterministic: sorted by stable id, never set/hash order."""
        return [self._by_id[k] for k in sorted(self._by_id)]
