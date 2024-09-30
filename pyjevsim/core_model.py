"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2024 Handong Global University
Copyright (c) 2014-2024 Hanbat National University
License: MIT.  The full license text is available at:
 - https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains CoreModel, the parent class of all Model Types. 
"""
from .system_object import SystemObject

class CoreModel(SystemObject):
    """
    All forms of Models in Pyjevsim have a CoreModel as their foundation. 
    CoreModel class serves as a base model with basic functionalities for input and output ports.
    """
    def __init__(self, _name, _type):
        """
        Args:
            _name (str): Model name
            _type (ModelType.BEHAVIORAL or ModelType.STRUCTURAL or ModelType.UTILITY): Model type
        """
        super().__init__()
        # Model Type
        self.model_type = _type
        self._name = _name

        # Input Ports Declaration
        self.external_input_ports = []
        # Output Ports Declaration
        self.external_output_ports = []

    def set_name(self, _name):
        """
        Sets the name of the model.
        
        Args:
            _name (str): New name of the model
        """
        self._name = _name

    def get_name(self):
        """
        Returns the name of the model.
        
        Returns:
            str: Name of the model
        """
        return self._name

    def get_model_type(self):
        """
        Returns the type of the model.
        
        Returns:
            (ModelType.BEHAVIORAL or ModelType.STRUCTURAL or ModelType.UTILITY) : Type of the model 
        """
        return self.model_type

    def insert_input_port(self, port):
        """Inserts an input port to the model.
        
        Args:
            port (str): Name of the input port
        """
        self.external_input_ports.append(port)

    def retrieve_input_ports(self):
        """
        Retrieves all input ports of the model.
        
        Returns:
            list: List of input ports
        """
        return self.external_input_ports

    def insert_output_port(self, port):
        """
        Inserts an output port to the model.
        
        Args:
            port (str): Name of the output port
        """
        self.external_output_ports.append(port)

    def retrieve_output_ports(self):
        """
        Retrieves all output ports of the model.
        
        Returns:
            list: List of output ports
        """
        return self.external_output_ports

    def model_snapshot(self):
        """
        Snapshot the information of the running model.
        
        Returns:
            dict: Dictionary containing model type, model name, and model data
        """
        model_info = {"type": self.model_type, "name": self._name, "data": self}
        return model_info