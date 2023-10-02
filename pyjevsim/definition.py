# Author: Changbeom Choi (@cbchoi)
# Copyright (c) 2014-2020 Handong Global University
# Copyright (c) 2014-2020 Hanbat National University
# License: MIT.  The full license text is available at:
#  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

from enum import Enum

# TODO-01 Define Error Type or Exception cbchoi
Infinite = float("inf") # hug value

class AttributeType(Enum):
    # BEHAVIOR = 0
    ASPECT = 1
    RUNTIME = 2
    UNKNOWN_TYPE = -1

    @staticmethod
    def resolve_type_from_str(name):
        if "ASPECT" == name.upper():
            return AttributeType.ASPECT
        elif "RUNTIME" == name.upper():
            return AttributeType.RUNTIME
        else:
            return AttributeType.UNKNOWN_TYPE

    @staticmethod
    def resolve_type_from_enum(enum):
        if enum == AttributeType.ASPECT:
            return "ASPECT"
        elif enum == AttributeType.RUNTIME:
            return "RUNTIME"
        else:
            return "UNKNOWN"

# 2019.05.16 added by cbchoi
class SimulationMode(Enum):
    SIMULATION_IDLE = 0         # Simulation Engine is instantiated but simulation is not running
    SIMULATION_RUNNING = 1      # Simulation Engine is instantiated, simulation is running
    SIMULATION_TERMINATED = 2   # Simulation Engine is instantiated but simulation is terminated
    SIMULATION_PAUSE = 3        # Simulation Engine is instantiated, simulation paused
    SIMULATION_UNKNOWN = -1     # Simulation Engine went to abnormal state

# 2020.01.20 added by cbchoi
class ModelType(Enum):
    BEHAVIORAL  = 0
    STRUCTURAL  = 1
    UTILITY     = 2

# 2023.10.01 added by cbchoi
class ExecutionType(Enum):
    R_TIME  = 0
    V_TIME  = 1

class SingletonType(object):
    def __call__(self, cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(SingletonType, cls).__call__(*args, **kwargs)
            return cls.__instance
