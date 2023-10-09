from pyjevsim.snapshot_manager import SnapshotManager

class SnapshotTest(SnapshotManager) :
    def __init__(self):
        super().__init__()
        
    def get_condition(self, name):
        if name == "Gen" :
            return self.snapshot_condition
    
    def snapshot_condition(dump_info):
        return True
