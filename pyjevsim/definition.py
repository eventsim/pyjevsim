"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains definitions for pyjevsim's const and type. 
"""
from enum import Enum

# Define an infinite value
Infinite = float("inf")

class AttributeType(Enum):
    """Enum for attribute types."""
    ASPECT = 1
    RUNTIME = 2
    UNKNOWN_TYPE = -1

    @staticmethod
    def resolve_type_from_str(name):
        """Resolves an attribute type from a string.
        
        Args:
            name (str): The name of the attribute type 
        Returns:
            AttributeType: The resolved attribute type 
        """
        
        if "ASPECT" == name.upper():
            return AttributeType.ASPECT
        elif "RUNTIME" == name.upper():
            return AttributeType.RUNTIME
        else:
            return AttributeType.UNKNOWN_TYPE

    @staticmethod
    def resolve_type_from_enum(enum):
        """Resolves an attribute type to a string.
        
        Args:
            enum (AttributeType): The attribute type enum 
        Returns:
            str: The name of the attribute type 
        """
        if enum == AttributeType.ASPECT:
            return "ASPECT"
        elif enum == AttributeType.RUNTIME:
            return "RUNTIME"
        else:
            return "UNKNOWN"

class SimulationMode(Enum):
    """Enum for simulation modes."""
    
    SIMULATION_IDLE = (
        0  # Simulation Engine is instantiated but simulation is not running
    )
    SIMULATION_RUNNING = 1  # Simulation Engine is instantiated, simulation is running 
    SIMULATION_TERMINATED = (
        2  # Simulation Engine is instantiated but simulation is terminated
    )
    SIMULATION_PAUSE = 3  # Simulation Engine is instantiated, simulation paused 
    SIMULATION_UNKNOWN = -1  # Simulation Engine went to abnormal state


class ModelType(Enum):
    """Enum for model types."""
    
    BEHAVIORAL = 0 #BehaviorModel type : DEVS Atomic Model
    STRUCTURAL = 1 #StructuralModel type : DEVS Coupled Model
    UTILITY = 2 


class ExecutionType(Enum):
    """Enum for execution types."""
    
    R_TIME = 0 #Real time
    V_TIME = 1 #Virtual time


class SingletonType(object):
    """A decorator for making a class a singleton."""
    
    def __call__(self, cls, *args, **kwargs):
        """Creates or returns the singleton instance of the class.
        
        Args:
            cls (type): The class to be instantiated
            *args: Variable length argument list 
            **kwargs: Arbitrary keyword arguments
        
        Returns:
            object: The singleton instance of the class
        """
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(SingletonType, cls).__call__(*args, **kwargs)
            return cls.__instance