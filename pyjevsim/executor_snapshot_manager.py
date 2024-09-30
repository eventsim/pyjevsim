"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""
""" This module contains an object, ExecutorSnapshotManager, that manages snapshots of the SysExecutor. """
from dill import loads, dumps
from .definition import ModelType

class ExecutorSnapshotManager:
    """Manager class for taking and loading snapshots of SysExecutor."""
    def __init__(self):
        pass

    def snapshot_executor(self, engine):
        """
        Take snapshot of Sysexecutor.        
        
        Args:
            engine(SysExecutor): SysExecutor to snapshot
        
        Returns:
            bytes: Serialized snapshot of the Sysexecutor
        """
        return dumps(engine.model_snapshot())

    def load_snapshot(self, shotengine):
        """
        Loads Sysexecutor snapshot.
        
        Args:
            shotengine (bytes): Serialized snapshot of the engine
        
        Returns:
            object(SysExecutor): loaded SysExecutor
                    
        """
        engine_info = loads(shotengine)
        
        if engine_info["type"] != ModelType.UTILITY:
            raise Exception(f"{engine_info['name']} is not of SystemExecutor type")
            #Exception: If the engine is not of type ModelType.UTILITY
        
        engine = engine_info["data"]
        return engine
    
    def cleansing(self, model):
        """
        Returns model that does not use a SnapshotExecutor as a BehaviorExecutor Type.
        
        Args:
            model(SnapshotExecutor): SnapshotExecutor to cleanse
        
        Returns:
            object: BehaviorExecutor
        """
        return model.get_behavior_executor()