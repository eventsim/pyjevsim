"""FOM bindings and position exchange used by the HLA AT/SIM examples.

The Platform attribute carries a whole physics object's end-of-tick state.
Both federates publish and subscribe the same ``fom_id``; the in-process bus
excludes the sender from a broadcast, so a federate never reflects its own
updates.
"""

from pyjevsim.hla import HLAAttribute
from utils.sensing import RemoteObject

PLATFORM_FOM = "AntiTorpedo.Platform"

PLATFORM_OUT = HLAAttribute(PLATFORM_FOM, direction="out", object_class="Platform")
PLATFORM_IN = HLAAttribute(PLATFORM_FOM, direction="in")

# FOM map for the Pitch backend (handle resolution + field encoding).
ANTITORPEDO_FOM_MAP = {
    PLATFORM_FOM: {
        "kind": "attribute",
        "class": "HLAobjectRoot.Platform",
        "fields": {
            "id": "string",
            "kind": "string",
            "x": "float64",
            "y": "float64",
            "z": "float64",
            "active": "int32",
        },
    },
}


class ProxySink:
    """Update the remote-object table from reflected attributes.

    The router calls this receiver synchronously rather than inserting a DEVS
    external event. Position exchange therefore remains at the driver-managed
    tick boundary.
    """

    def __init__(self, ctx):
        self.ctx = ctx

    def _on_rti_event(self, kind, fom_id, payload, timestamp):
        d = payload[0]
        sid = d["id"]
        if int(d["active"]) == 0:
            self.ctx.remote.pop(sid, None)
        else:
            self.ctx.remote[sid] = RemoteObject(
                sid, d["kind"], d["x"], d["y"], d["z"], True
            )


def publish_local(ctx, transport):
    """Broadcast every local object's end-of-tick position, plus active=0
    tombstones for objects pruned since the last publish."""
    for o in ctx.items:
        x, y, z = o.get_position()
        transport.send(PLATFORM_OUT, [{
            "id": o.sense_id, "kind": o.kind,
            "x": x, "y": y, "z": z,
            "active": 1 if o.check_active() else 0,
        }])
    for sid in ctx.removed:
        transport.send(PLATFORM_OUT, [{
            "id": sid, "kind": "decoy",
            "x": 0.0, "y": 0.0, "z": 0.0, "active": 0,
        }])
    ctx.removed.clear()
