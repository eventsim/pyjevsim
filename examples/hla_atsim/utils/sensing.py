"""Per-tick position snapshots for the AT/SIM examples.

Detectors read positions captured at the end of the preceding tick instead of
live ``ObjectDB`` entries. Entries are ordered by ``sense_id``. A standalone
run supplies local objects; an HLA run also supplies reflected remote objects.
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
    """Position values for one tick, keyed by ``sense_id``."""

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
        """Return entries sorted by ``sense_id``."""
        return [self._by_id[k] for k in sorted(self._by_id)]
