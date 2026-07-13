"""Per-federate simulation context — replaces the global ObjectDB singleton.

A singleton is fatal for the HLA build: ``run_hla_inprocess.py`` runs *two*
``SysExecutor`` federates in one process, and each federate needs its own
``items``/``decoys``/owning ``executor``/``snapshot``. Standalone uses one
shared ``SimContext``; HLA uses two (one per federate).
"""

from utils.sensing import PositionSnapshot


class SimContext:
    def __init__(self):
        self.items = []        # local physics objs (ManueverObject + decoy objs)
        self.decoys = []       # list of (name, obj)
        self.removed = []      # sense_ids pruned this tick (HLA -> active=0)
        self.executor = None   # the SysExecutor this platform runs in
        self.snapshot = PositionSnapshot()
        self.remote = {}       # sense_id -> RemoteObject (HLA reflected peers)
        self.tick = 0          # current tick index (armed by commit_tick)

    def set_executor(self, se):
        self.executor = se

    def get_executor(self):
        return self.executor
